# backend/voice/speech_manager.py
import requests
import os
from pathlib import Path
from .silero_tts import synthesize_silero

OPENTTS_URL = "http://127.0.0.1:5500"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "static" / "audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def synthesize_tts(text: str, filename: str = "reya_output.wav") -> str:
    """Try Coqui (via OpenTTS) first, then Silero."""
    audio_path = OUTPUT_DIR / filename
    try:
        # 🎙️ Try Coqui XTTS via OpenTTS
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

    # 🔊 Fallback to Silero
    return synthesize_silero(text, str(audio_path))
