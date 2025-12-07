# backend/voice/stt.py
import os
import random
import wave
import asyncio
import tempfile
import traceback
from pathlib import Path
from typing import Optional

import pyaudio
from fuzzywuzzy import fuzz

from backend.stt.whisper_cpp import transcribe_whisper_cpp
from backend.voice.speech_manager import synthesize_tts

# -------------------------------------------------------
# WAKE WORDS / CONFIG
# -------------------------------------------------------
WAKE_WORDS = ["reya", "rea", "raya", "rhea", "hey reya", "ok reya"]
MIN_WAKE_CONFIDENCE = 80

WAKE_REPLIES = [
    "I'm listening.",
    "Yes? What’s on your mind?",
    "Go ahead, I’m here.",
    "Mm? You called for me?",
    "Right here. What do you need?",
    "Listening~",
    "Hm? Oh—yes, I hear you.",
    "At your service.",
    "Have I been summoned? Very well then, speak.",
]

# PyAudio recording defaults — matches whisper/common 16k input
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000


# -------------------------------------------------------
# FUZZY WAKE WORD MATCH
# -------------------------------------------------------
def match_wake_word(text: str) -> bool:
    text = (text or "").lower().strip()
    for wake in WAKE_WORDS:
        score = fuzz.ratio(wake, text)
        if score >= MIN_WAKE_CONFIDENCE:
            print(f"[WakeWord] '{text}' matched '{wake}' ({score}%)")
            return True
    return False


# -------------------------------------------------------
# RANDOMIZED WAKE RESPONSE (runs synth on a thread)
# -------------------------------------------------------
async def speak_wake_reply(reya) -> None:
    reply = random.choice(WAKE_REPLIES)
    try:
        # synthesize_tts is synchronous (returns file path) so run in thread
        await asyncio.to_thread(synthesize_tts, reply)
    except Exception as e:
        print(f"[WakeReply ERROR] {e}")


# -------------------------------------------------------
# MICROPHONE CAPTURE (PyAudio) — returns path to WAV file
# -------------------------------------------------------
def _record_microphone_to_temp(seconds: int = 3, device_index: Optional[int] = None) -> str:
    """
    Record `seconds` of microphone audio to a temp WAV file and return its path.
    This function is synchronous (blocking) and uses PyAudio.
    """
    p = None
    tmp_fpath = None
    try:
        p = pyaudio.PyAudio()

        # open stream (might raise OSError if no device)
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=device_index,
        )

        frames = []
        # read loop — protect against short read errors
        total_reads = int(RATE / CHUNK * max(1, seconds))
        for _ in range(total_reads):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                # on read error, append silence for this chunk
                print(f"[Mic read warning] {e}")
                data = (b"\x00" * CHUNK * 2)  # paInt16 -> 2 bytes/sample
            frames.append(data)

        stream.stop_stream()
        stream.close()

        # write to temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_fpath = tmp.name
        tmp.close()

        wf = wave.open(tmp_fpath, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
        wf.close()

        return tmp_fpath

    finally:
        try:
            if p is not None:
                p.terminate()
        except Exception:
            pass


# -------------------------------------------------------
# ALWAYS-LISTENING WAKE DETECTOR (async)
# -------------------------------------------------------
async def wait_for_wake_word(reya, test_mode: bool = False, model_size: str = "small") -> bool:
    """
    Always-listening loop that records short slices to temp files,
    transcribes with whisper.cpp, and returns True when wake word matched.
    """
    print("🎧 Whisper.cpp Always-Listening Enabled – waiting for wake word…")
    while True:
        try:
            # record 1s slice
            temp_path = await asyncio.to_thread(_record_microphone_to_temp, 1)

            try:
                text = await asyncio.to_thread(transcribe_whisper_cpp, temp_path, "small")

                text = (text or "").lower().strip()
            except Exception as e:
                # log and continue — do not crash the wake loop
                print(f"[Wake STT error] {e}")
                text = ""

            # cleanup temporary file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

            if test_mode:
                print(f"[Wake DEBUG] Heard: {text}")

            if text and match_wake_word(text):
                # spawn wake reply but don't await here (background)
                asyncio.create_task(speak_wake_reply(reya))
                return True

        except Exception as e:
            print(f"[Wake loop error] {e}\n{traceback.format_exc()}")
            # short backoff to avoid hot-looping on device errors
            await asyncio.sleep(0.5)


# -------------------------------------------------------
# LISTEN FOR A COMMAND (after wake) — async
# -------------------------------------------------------
async def listen_for_command(reya, max_seconds: int = 8, model_size: str = "large") -> str:
    """
    Record up to `max_seconds`, transcribe with Whisper.cpp and return the text.
    Returns a friendly fallback string on total failure.
    """
    print("🎤 Listening for command…")
    try:
        temp_path = await asyncio.to_thread(_record_microphone_to_temp, max_seconds)
    except Exception as e:
        print(f"[listen_for_command] mic record failed: {e}")
        return "I didn’t catch that."

    try:
        text = await asyncio.to_thread(transcribe_whisper_cpp, temp_path, "large")

        return (text or "").strip()
    except Exception as e:
        print(f"[Command STT ERROR] {e}\n{traceback.format_exc()}")
        return "I didn’t catch that."
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass
