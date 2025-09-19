# backend/edge_tts.py
import os, re, asyncio, tempfile
from typing import Tuple, Dict, Any, Optional
from uuid import uuid4
import edge_tts

try:
    from pydub import AudioSegment
    from pydub.playback import play
    _PYDUB_OK = True
except Exception:
    _PYDUB_OK = False

STATIC_DIR = os.path.join("static")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

def get_voice_and_preset(reya) -> Tuple[str, Dict[str, Any]]:
    style_to_voice = {
        "oracle":     "en-US-JennyNeural",
        "griot":      "en-US-AriaNeural",
        "cyberpunk":  "en-US-AmberNeural",
        "zen":        "en-GB-LibbyNeural",
        "detective":  "en-US-AnaNeural",
        "companion":  "en-GB-MiaNeural",
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

def _normalize_text(text: str, max_len: int = 8000) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned[:max_len]

def default_voice_for_text(text: str) -> str:
    # kana/kanji → JP or ZH; prefer JP if kana present
    jp_kana = any("\u3040" <= ch <= "\u30ff" for ch in text)
    cjk     = any("\u4e00" <= ch <= "\u9fff" for ch in text)
    if jp_kana:
        return "ja-JP-NanamiNeural"
    if cjk:
        return "zh-CN-XiaoxiaoNeural"
    return "en-US-JennyNeural"

async def synthesize_to_file(
    text: str,
    reya=None,
    out_path: str = "",
    voice_override: Optional[str] = None,
) -> str:
    text = _normalize_text(text)
    if not text:
        raise ValueError("Empty text for TTS.")

    # choose voice
    if voice_override:
        voice = voice_override
        preset = {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"}
    else:
        base_voice, preset = get_voice_and_preset(reya)
        voice = base_voice or default_voice_for_text(text)

    communicate = edge_tts.Communicate(
        text,
        voice=voice,
        rate=preset.get("rate", "+0%"),
        pitch=preset.get("pitch", "+0Hz"),
        volume=preset.get("volume", "+0%"),
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    await communicate.save(out_path)
    return out_path

async def synthesize_to_static_url(text: str, reya=None, voice_override: Optional[str] = None) -> str:
    filename = f"{uuid4()}.mp3"
    fs_path = os.path.join(AUDIO_DIR, filename)
    await synthesize_to_file(text, reya, fs_path, voice_override=voice_override)
    return f"/static/audio/{filename}"

async def speak_with_voice_style_async(text: str, reya=None, voice_override: Optional[str] = None) -> None:
    text = _normalize_text(text)
    if not text:
        print("[TTS] Empty text, skipping playback.")
        return

    if voice_override:
        voice = voice_override
        preset = {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"}
    else:
        base_voice, preset = get_voice_and_preset(reya)
        voice = base_voice or default_voice_for_text(text)

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

def speak_with_voice_style(text: str, reya=None, voice_override: Optional[str] = None) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        asyncio.create_task(speak_with_voice_style_async(text, reya, voice_override=voice_override))
    else:
        asyncio.run(speak_with_voice_style_async(text, reya, voice_override=voice_override))
