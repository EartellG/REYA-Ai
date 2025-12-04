# backend/voice/speech_manager.py

import os
import requests
import simpleaudio as sa
from pathlib import Path

from .silero_tts import synthesize_silero
from backend.stt.whisper_cpp import transcribe_whisper_cpp

OPENTTS_URL = "http://127.0.0.1:5500"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "static" / "audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------
#  TTS SYNTHESIS (Coqui → Silero fallback)
# ------------------------------
def synthesize_tts(text: str, filename: str = "reya_output.wav") -> str:
    """
    Generate TTS audio.
    1) Try Coqui XTTS (via OpenTTS)
    2) Fallback to Silero
    """
    audio_path = OUTPUT_DIR / filename

    try:
        resp = requests.post(
            f"{OPENTTS_URL}/api/tts",
            json={"text": text, "voice": "coqui-xtts-v2", "lang": "en"},
            timeout=10,
        )

        if resp.status_code == 200:
            with open(audio_path, "wb") as f:
                f.write(resp.content)
            return str(audio_path)
        else:
            print(f"[WARN] Coqui failed ({resp.status_code}), fallback → Silero")

    except Exception as e:
        print(f"[ERROR] Coqui XTTS unavailable: {e}, fallback → Silero")

    # fallback to Silero
    return synthesize_silero(text, str(audio_path))


# ------------------------------
#  AUDIO PLAYER
# ------------------------------
def play_audio(path: str):
    """Plays a WAV file using simpleaudio."""
    try:
        wave_obj = sa.WaveObject.from_wave_file(path)
        play_obj = wave_obj.play()
        play_obj.wait_done()
    except Exception as e:
        print(f"[Audio ERROR] Could not play audio: {e}")


# ------------------------------
#  UNIFIED TTS OUTPUT FOR REYA
# ------------------------------
def speak_tts(text: str, filename="reya_output.wav"):
    """
    The single function REYA uses to speak.
    - Generates audio
    - Plays it back
    """
    print(f"[REYA TTS] Speaking: {text}")

    try:
        path = synthesize_tts(text, filename)
        play_audio(path)
    except Exception as e:
        print(f"[speak_tts ERROR] {e}")
