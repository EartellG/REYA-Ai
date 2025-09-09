# backend/edge_tts.py
import os
import re
import asyncio
import tempfile
from typing import Tuple, Dict, Any
from uuid import uuid4

import edge_tts

SIGNATURE = "edge_tts build: synced"
# Optional playback deps; keep them guarded
try:
    from pydub import AudioSegment
    from pydub.playback import play
    _PYDUB_OK = True
except Exception:
    _PYDUB_OK = False

# ---------- Config ----------
STATIC_DIR = os.path.join("static")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


# ---------- (Legacy) style mapping ----------
# Kept for backward-compat, but we now PREFER reya.voice/preset when present.
def get_voice_and_preset(reya) -> Tuple[str, Dict[str, Any]]:
    style_to_voice = {
        "oracle": "en-US-JennyNeural",
        "griot": "en-US-GuyNeural",
        "cyberpunk": "en-US-DavisNeural",
        "zen": "en-US-AriaNeural",
        "detective": "en-US-ChristopherNeural",
        "companion": "en-GB-MiaNeural",
    }

    style = getattr(reya, "style", "companion")
    voice = style_to_voice.get(style, "en-GB-MiaNeural")

    preset = {
        "oracle":     {"rate": "+20%", "pitch": "+45Hz", "volume": "+0%"},
        "griot":      {"rate": "+0%",  "pitch": "-1Hz",  "volume": "+0%"},
        "cyberpunk":  {"rate": "+10%", "pitch": "+4Hz",  "volume": "+0%"},
        "zen":        {"rate": "-10%", "pitch": "-4Hz",  "volume": "+0%"},
        "detective":  {"rate": "-5%",  "pitch": "-2Hz",  "volume": "+0%"},
        "companion":  {"rate": "+0%",  "pitch": "+15Hz", "volume": "+0%"},
    }.get(style, {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"})

    return voice, preset


# ---------- Utilities ----------
def _normalize_text(text: str, max_len: int = 8000) -> str:
    # collapse excessive whitespace and clamp length for safety
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned[:max_len]

def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

def _reya_voice(reya) -> str:
    # Prefer explicit voice on the Reya personality; fallback to style map
    return getattr(reya, "voice", None) or get_voice_and_preset(reya)[0]

def _reya_preset(reya) -> Dict[str, Any]:
    # Prefer explicit preset on the Reya personality; fallback to style map
    return getattr(reya, "preset", None) or get_voice_and_preset(reya)[1]


# ---------- 1) Save-to-file (for frontend playback) ----------
async def synthesize_to_file(text: str, reya, out_path: str) -> str:
    """
    Synthesize `text` using Edge TTS and save to `out_path` (mp3).
    Returns the filesystem path.
    """
    text = _normalize_text(text)
    if not text:
        raise ValueError("Empty text for TTS.")

    voice = _reya_voice(reya)
    preset = _reya_preset(reya)

    communicate = edge_tts.Communicate(
        text,
        voice=voice,
        rate=preset.get("rate", "+0%"),
        pitch=preset.get("pitch", "+0Hz"),
        volume=preset.get("volume", "+0%"),
    )
    _ensure_parent(out_path)
    await communicate.save(out_path)
    return out_path


async def synthesize_to_static_url(text: str, reya) -> str:
    """
    Synthesize to `static/audio/<uuid>.mp3` and return a URL path
    like `/static/audio/<uuid>.mp3` suitable for the frontend.
    """
    filename = f"{uuid4()}.mp3"
    fs_path = os.path.join(AUDIO_DIR, filename)
    await synthesize_to_file(text, reya, fs_path)
    return f"/static/audio/{filename}"


# ---------- 2) Optional server-side playback ----------
async def speak_with_voice_style_async(text: str, reya) -> None:
    """
    Server-side local playback:
    - Saves to a temp mp3
    - Plays via pydub (if available)
    - Deletes temp file
    """
    text = _normalize_text(text)
    if not text:
        print("[TTS] Empty text, skipping playback.")
        return

    voice = _reya_voice(reya)
    preset = _reya_preset(reya)

    communicate = edge_tts.Communicate(
        text,
        voice=voice,
        rate=preset.get("rate", "+0%"),
        pitch=preset.get("pitch", "+0Hz"),
        volume=preset.get("volume", "+0%"),
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_name = tmp_file.name

    try:
        await communicate.save(tmp_name)
        if _PYDUB_OK:
            try:
                audio = AudioSegment.from_file(tmp_name, format="mp3")
                play(audio)
            except Exception as e:
                print(f"[ERROR] Playback failed: {e}")
        else:
            print("[TTS] pydub/ffmpeg not available; skipping playback.")
    finally:
        try:
            os.remove(tmp_name)
        except Exception:
            pass


def speak_with_voice_style(text: str, reya) -> None:
    """
    Safe to call from both script and FastAPI contexts.
    - If no running loop: runs a new loop (script usage).
    - If already in an event loop (e.g., FastAPI): schedules a background task.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        asyncio.create_task(speak_with_voice_style_async(text, reya))
    else:
        asyncio.run(speak_with_voice_style_async(text, reya))
