# backend/voice/stt.py

import os
import random
import asyncio
import speech_recognition as sr
from fuzzywuzzy import fuzz
from pathlib import Path

from backend.stt.whisper_cpp import transcribe_whisper_cpp
from backend.voice.edge_tts import speak_with_voice_style
from backend.voice.speech_manager import synthesize_tts

# --- Microphone setup ---
recognizer = sr.Recognizer()
mic = sr.Microphone()

# --- Wake words ---
WAKE_WORDS = ["reya", "rea", "raya", "rhea", "hey reya", "ok reya"]
MIN_WAKE_CONFIDENCE = 80

# Personality-based randomized REYA wake replies
WAKE_REPLIES = [
    "I'm listening.",
    "Yes? What’s on your mind?",
    "Go ahead, I’m here.",
    "Mm? You called for me?",
    "Right here. What do you need?",
    "Listening~",
    "Hm? Oh—yes, I hear you.",
    "At your service.",
    "Have I been Summoned? very well then, speak.",
]

# -------------------------------------------------------
# Wake-word fuzzy match
# -------------------------------------------------------
def match_wake_word(text: str) -> bool:
    for wake in WAKE_WORDS:
        score = fuzz.ratio(wake, text)
        if score >= MIN_WAKE_CONFIDENCE:
            print(f"[Wake Match] '{text}' → {wake} ({score}%)")
            return True
    return False


# -------------------------------------------------------
# RANDOMIZED personality wake reply
# -------------------------------------------------------
async def speak_wake_reply(reya):
    reply = random.choice(WAKE_REPLIES)
    try:
        await asyncio.to_thread(speak_with_voice_style, reply, reya)
    except Exception:
        # fallback to silent fail — we never want wake to break STT
        print("[Wake Reply] TTS unavailable, skipping.")


# -------------------------------------------------------
# ALWAYS-LISTENING WAKE WORD DETECTOR
# - Quiet background listener
# - When wake word spoken → returns control to REYA main loop
# -------------------------------------------------------
def wait_for_wake_word(reya, test_mode=False):
    print("🎧 Always-listening enabled… waiting for wake word…")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)

        while True:
            try:
                audio = recognizer.listen(source)
                text = recognizer.recognize_google(audio).lower()

                if test_mode:
                    print(f"[DEBUG] Heard: {text}")

                if match_wake_word(text):
                    asyncio.create_task(speak_wake_reply(reya))
                    return True

            except sr.UnknownValueError:
                continue
            except Exception as e:
                print(f"[Wake Error] {e}")
                continue


# -------------------------------------------------------
# LOCAL STT PIPELINE:
# Whisper.cpp → Google SR fallback → graceful fail
# -------------------------------------------------------
def transcribe_audio(audio_path: str) -> str:
    """
    Attempts Whisper.cpp first.
    Falls back to speech_recognition → Google Web STT.
    And falls back to a safe string on total failure.
    """
    # ---------------------------
    # Whisper.cpp FIRST
    # ---------------------------
    try:
        print("[STT] Trying Whisper.cpp…")
        text = transcribe_whisper_cpp(audio_path)
        if text.strip():
            print("[STT] Whisper.cpp success.")
            return text.strip()
    except Exception as e:
        print(f"[STT Whisper.cpp failed] {e}")

    # ---------------------------
    # Google fallback (SpeechRecognition)
    # ---------------------------
    try:
        print("[STT] Trying Google SpeechRecognition fallback…")
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        print("[STT] Google SR success.")
        return text.lower().strip()
    except Exception as e:
        print(f"[STT Google fallback failed] {e}")

    # Total failure → safe, graceful
    print("[STT] Total failure. Returning fallback text.")
    return "I didn't catch that."


# -------------------------------------------------------
# DIRECT MICROPHONE COMMAND LISTENER (after wake word)
# -------------------------------------------------------
def listen_for_command(reya, timeout=10, phrase_time_limit=15):
    print("🎤 Listening for command…")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return "I didn’t hear anything."

    # Save temp wav
    temp_path = Path(__file__).resolve().parent / "temp_cmd.wav"
    with open(temp_path, "wb") as f:
        f.write(audio.get_wav_data())

    return transcribe_audio(str(temp_path))
