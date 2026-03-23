# backend/voice/stt.py
import os
import wave
import asyncio
import tempfile
import traceback
import audioop
from typing import Optional, Tuple, List

import pyaudio
from fuzzywuzzy import fuzz

from backend.stt.whisper_cpp import transcribe_whisper_cpp

# -------------------------------------------------------
# WAKE WORDS / CONFIG
# -------------------------------------------------------
WAKE_WORDS = ["reya", "rea", "raya", "rhea", "hey reya", "ok reya"]
MIN_WAKE_CONFIDENCE = 80

# Adaptive RMS thresholding (calibrate noise floor at startup)
CALIBRATION_SECONDS = 2.0
RMS_MULTIPLIER = 2.5          # louder than baseline counts as speech
RMS_FLOOR_ADD = 60            # absolute gap above baseline
MIN_SPEECH_RMS = 80           # never treat below this as speech

WAKE_REPLIES = [
    "I'm listening.",
    "Yes? What’s on your mind?",
    "Go ahead, I’m here.",
    "Mm? You called for me?",
    "Right here. What do you need?",
    "Listening~",
    "Hm? Oh—yes, I hear you.",
    "At your service.",
    "Have I been summoned? Very well then, what can I do for you?",
]

# PyAudio recording defaults
CHUNK = 1024
FORMAT = pyaudio.paInt16

# Wake slices: slightly longer helps whisper not return empty
WAKE_SLICE_SECONDS = 1.5
CALIBRATION_SLICE_SECONDS = 0.25


# -------------------------------------------------------
# DEVICE HELPERS
# -------------------------------------------------------
def _list_input_devices() -> List[Tuple[int, str, int]]:
    """Return [(index, name, maxInputChannels), ...] for input-capable devices."""
    p = pyaudio.PyAudio()
    out: List[Tuple[int, str, int]] = []
    try:
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            ch = int(info.get("maxInputChannels", 0))
            if ch > 0:
                out.append((i, str(info.get("name", "Unknown")), ch))
    finally:
        p.terminate()
    return out


def _pick_device_index() -> Optional[int]:
    """
    Choose mic device index.
    Priority:
      1) REYA_MIC_INDEX env var
      2) PyAudio default input device
      3) first input-capable device that is not obviously bad
    """
    bad_name_fragments = [
        "usb audio device",      # your broken controller/headset path
        "hd audio mixed capture" # noisy loopback-ish path
    ]

    def is_bad_device_name(name: str) -> bool:
        lowered = name.lower()
        return any(fragment in lowered for fragment in bad_name_fragments)

    env = os.getenv("REYA_MIC_INDEX", "").strip()
    if env.isdigit():
        return int(env)

    p = pyaudio.PyAudio()
    try:
        try:
            info = p.get_default_input_device_info()
            default_idx = info.get("index")
            default_name = str(info.get("name", ""))
            if default_idx is not None and not is_bad_device_name(default_name):
                return int(default_idx)
        except Exception:
            pass
    finally:
        p.terminate()

    devs = _list_input_devices()
    for idx, name, _ch in devs:
        if not is_bad_device_name(name):
            return idx

    return devs[0][0] if devs else None


def _compute_speech_threshold(baseline_rms: int) -> int:
    return max(int(baseline_rms * RMS_MULTIPLIER), baseline_rms + RMS_FLOOR_ADD, MIN_SPEECH_RMS)


def _calibrate_noise_floor(device_index: Optional[int]) -> int:
    """
    Records short slices for a few seconds and estimates baseline noise RMS.
    Uses median (robust to spikes).
    """
    slices = int(CALIBRATION_SECONDS / CALIBRATION_SLICE_SECONDS)
    rms_vals: List[int] = []

    for _ in range(max(1, slices)):
        path, rms = _record_microphone_to_temp(CALIBRATION_SLICE_SECONDS, device_index)
        rms_vals.append(rms)
        try:
            os.unlink(path)
        except Exception:
            pass

    rms_vals.sort()
    if not rms_vals:
        return 20
    return int(rms_vals[len(rms_vals) // 2])


# -------------------------------------------------------
# FUZZY WAKE WORD MATCH
# -------------------------------------------------------
def match_wake_word(text: str, debug: bool = False) -> bool:
    text = (text or "").lower().strip()
    if not text:
        return False

    best = ("", 0)
    for wake in WAKE_WORDS:
        score = fuzz.ratio(wake, text)
        if score > best[1]:
            best = (wake, score)
        if score >= MIN_WAKE_CONFIDENCE:
            print(f"[WakeWord] ✅ '{text}' matched '{wake}' ({score}%)")
            return True

    if debug:
        print(f"[WakeWord] ❌ best match for '{text}' was '{best[0]}' ({best[1]}%)")
    return False


# -------------------------------------------------------
# MICROPHONE CAPTURE (PyAudio) — returns (wav_path, avg_rms)
# -------------------------------------------------------
def _record_microphone_to_temp(seconds: float = 1.0, device_index: Optional[int] = None) -> Tuple[str, int]:
    """
    Record `seconds` of microphone audio to a temp WAV file and return (path, avg_rms).
    Uses device default sample rate and channels for best compatibility on Windows.
    """
    p = None
    frames: List[bytes] = []
    rms_total = 0
    tmp_fpath = None

    try:
        p = pyaudio.PyAudio()

        info = (
            p.get_device_info_by_index(device_index)
            if device_index is not None
            else p.get_default_input_device_info()
        )

        device_rate = int(info.get("defaultSampleRate", 48000))
        device_channels = int(info.get("maxInputChannels", 1))
        device_channels = 1 if device_channels < 1 else min(device_channels, 2)  # cap at 2

        stream = p.open(
            format=FORMAT,
            channels=device_channels,
            rate=device_rate,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=device_index,
        )

        total_reads = int((device_rate / CHUNK) * max(0.1, float(seconds)))

        for _ in range(max(1, total_reads)):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                print(f"[Mic read warning] {e}")
                # paInt16 = 2 bytes/sample, multiply by channels
                data = b"\x00" * CHUNK * 2 * device_channels

            frames.append(data)

            try:
                rms_total += audioop.rms(data, 2)
            except Exception:
                pass

        stream.stop_stream()
        stream.close()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_fpath = tmp.name
        tmp.close()

        wf = wave.open(tmp_fpath, "wb")
        wf.setnchannels(device_channels)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(device_rate)
        wf.writeframes(b"".join(frames))
        wf.close()

        avg_rms = int(rms_total / max(1, total_reads))
        return tmp_fpath, avg_rms

    finally:
        try:
            if p is not None:
                p.terminate()
        except Exception:
            pass


# -------------------------------------------------------
# ALWAYS-LISTENING WAKE DETECTOR (async)
# -------------------------------------------------------
async def wait_for_wake_word(
    reya,
    test_mode: bool = False,
    model_size: str = "small",
) -> bool:
    """
    Always-listening loop:
      - calibrates baseline noise RMS
      - records short slices to temp wav
      - skips transcription if under adaptive speech threshold
      - transcribes with whisper.cpp
      - returns True when wake word matched
    """
    device_index = _pick_device_index()

    if test_mode:
        devs = _list_input_devices()
        print("🎛️  Input devices detected:")
        for i, name, ch in devs:
            print(f"   - [{i}] {name} (channels={ch})")
        print(f"🎙️  Using input device index: {device_index} (set REYA_MIC_INDEX to override)")
        print(f"🧠 Whisper model_size for wake: {model_size}")

    baseline = await asyncio.to_thread(_calibrate_noise_floor, device_index)
    speech_thresh = _compute_speech_threshold(baseline)

    if test_mode:
        print(f"🎚️  Noise baseline={baseline}  speech_thresh={speech_thresh}")

    print("🎧 Whisper.cpp Always-Listening Enabled – waiting for wake word…")

    while True:
        try:
            temp_path, rms = await asyncio.to_thread(_record_microphone_to_temp, WAKE_SLICE_SECONDS, device_index)

            if rms < speech_thresh:
                if test_mode:
                    print(f"[Wake DEBUG] (silence) rms={rms}")
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                await asyncio.sleep(0.05)
                continue

            try:
                text = await asyncio.to_thread(transcribe_whisper_cpp, temp_path, model_size)
                text = (text or "").lower().strip()
            except Exception as e:
                print(f"[Wake STT error] {e}")
                text = ""

            try:
                os.unlink(temp_path)
            except Exception:
                pass

            if test_mode:
                print(f"[Wake DEBUG] rms={rms} heard: {text}")

            if (not test_mode) and text:
                print(f"[Wake] heard: {text}")

            if text and match_wake_word(text, debug=test_mode):
                return True

        except Exception as e:
            print(f"[Wake loop error] {e}\n{traceback.format_exc()}")
            await asyncio.sleep(0.5)


# -------------------------------------------------------
# LISTEN FOR A COMMAND (after wake) — async
# -------------------------------------------------------
async def listen_for_command(reya, max_seconds: int = 8, model_size: str = "large") -> str:
    """
    Record up to `max_seconds`, transcribe with Whisper.cpp and return the text.
    Uses the same adaptive thresholding approach to skip obvious silence.
    """
    device_index = _pick_device_index()
    print(f"🎤 Listening for command… (device={device_index}, model={model_size})")

    # quick baseline calibration (shorter than wake)
    baseline = await asyncio.to_thread(_calibrate_noise_floor, device_index)
    speech_thresh = _compute_speech_threshold(baseline)

    try:
        temp_path, rms = await asyncio.to_thread(_record_microphone_to_temp, float(max_seconds), device_index)
    except Exception as e:
        print(f"[listen_for_command] mic record failed: {e}")
        return ""

    try:
        if rms < speech_thresh:
            print(f"[Command] (silence) rms={rms} (thresh={speech_thresh})")
            return ""

        text = await asyncio.to_thread(transcribe_whisper_cpp, temp_path, model_size)
        return (text or "").strip()

    except Exception as e:
        print(f"[Command STT ERROR] {e}\n{traceback.format_exc()}")
        return ""
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass