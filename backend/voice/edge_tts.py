# backend/voice/edge_tts.py
# Azure Speech first (preferred), optional Edge TTS fallback.
# Produces MP3 bytes / files under static/audio. No SAPI fallback.

import os, re, asyncio, tempfile
from typing import Tuple, Dict, Any, Optional
from uuid import uuid4
from pathlib import Path

# Optional: load .env here so flags exist even during hot-reload imports
try:
    from dotenv import load_dotenv  # pip install python-dotenv
    load_dotenv()
except Exception:
    pass

# ----------------------- Project/static paths -------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # backend/
STATIC_DIR   = PROJECT_ROOT / "static"
AUDIO_DIR    = STATIC_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------- Optional server-side playback ----------------
try:
    from pydub import AudioSegment
    from pydub.playback import play
    _PYDUB_OK = True
except Exception:
    _PYDUB_OK = False

# ----------------------- Runtime config -------------------------------
def _cfg() -> Dict[str, Any]:
    """Read env at call time so hot reload & .env changes are honored."""
    return {
        "AZURE_KEY":    os.getenv("AZURE_SPEECH_KEY") or "",
        "AZURE_REGION": os.getenv("AZURE_SPEECH_REGION") or "",
        "EDGE_ENABLED": (os.getenv("REYA_TTS_EDGE_ENABLED", "0") == "1"),
    }

def engine_status() -> Dict[str, Any]:
    c = _cfg()
    return {
        "azure_present": bool(c["AZURE_KEY"] and c["AZURE_REGION"]),
        "region": c["AZURE_REGION"] or None,
        "edge_enabled": c["EDGE_ENABLED"],
    }

# ----------------------- Voices & text utils --------------------------
def get_voice_and_preset(reya) -> Tuple[str, Dict[str, Any]]:
    style_to_voice = {
        "oracle":     "en-US-JennyNeural",
        "griot":      "en-US-AriaNeural",
        "cyberpunk":  "en-US-AmberNeural",
        "zen":        "en-GB-LibbyNeural",
        "detective":  "en-US-AnaNeural",
        "companion":  "en-GB-SoniaNeural",  # Mia removed
    }
    style = getattr(reya, "style", "companion")
    voice = style_to_voice.get(style, "en-GB-SoniaNeural")
    preset = {
        "oracle":     {"rate": "+20%", "volume": "+0%"},
        "griot":      {"rate": "+0%",  "volume": "+0%"},
        "cyberpunk":  {"rate": "+10%", "volume": "+0%"},
        "zen":        {"rate": "-10%", "volume": "+0%"},
        "detective":  {"rate": "-5%",  "volume": "+0%"},
        "companion":  {"rate": "+0%",  "volume": "+0%"},
    }.get(style, {"rate": "+0%", "volume": "+0%"})
    return voice, preset

def _normalize_text(text: str, max_len: int = 8000) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned[:max_len]

def default_voice_for_text(text: str) -> str:
    jp_kana = any("\u3040" <= ch <= "\u30ff" for ch in text)
    cjk     = any("\u4e00" <= ch <= "\u9fff" for ch in text)
    if jp_kana:
        return "ja-JP-NanamiNeural"
    if cjk:
        return "zh-CN-XiaoxiaoNeural"
    return "en-US-JennyNeural"

# ----------------------- Azure helper ---------------------------------
def _azure_sync_speak(text: str, voice: str) -> bytes:
    import azure.cognitiveservices.speech as speechsdk
    c = _cfg()
    speech_config = speechsdk.SpeechConfig(
        subscription=c["AZURE_KEY"],
        region=c["AZURE_REGION"]
    )
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3
    )
    speech_config.speech_synthesis_voice_name = voice or "en-GB-SoniaNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text(text)
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        if not result.audio_data:
            raise RuntimeError("Azure returned empty audio_data.")
        return result.audio_data
    if result.reason == speechsdk.ResultReason.Canceled:
        details = speechsdk.CancellationDetails(result)
        raise RuntimeError(f"Azure canceled: {details.reason} {details.error_details}")
    raise RuntimeError("Azure synthesis failed (unknown reason).")

async def _azure_synth_to_bytes(text: str, voice: str) -> Tuple[bytes, dict]:
    loop = asyncio.get_running_loop()
    audio = await loop.run_in_executor(None, _azure_sync_speak, text, voice)
    return audio, {"engine": "azure_speech", "voice": voice, "content_type": "audio/mpeg"}

# ----------------------- Edge helper (optional) -----------------------
async def _edge_synth_to_bytes(text: str, voice: str, rate: str = "+0%", volume: str = "+0%") -> Tuple[bytes, dict]:
    import edge_tts
    tts = edge_tts.Communicate(text, voice=voice, rate=rate, volume=volume)
    chunks: list[bytes] = []
    async for chunk in tts.stream():
        if chunk.get("type") == "audio":
            chunks.append(chunk.get("data", b""))
    if not chunks:
        raise RuntimeError("Edge TTS returned no audio.")
    return b"".join(chunks), {"engine": "edge_tts", "voice": voice, "content_type": "audio/mpeg"}

# ----------------------- Public API (bytes) ---------------------------
async def synth_to_bytes(
    text: str,
    voice: str = "en-GB-SoniaNeural",
    rate: str = "+0%",
    volume: str = "+0%",
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Azure → Edge (if enabled). Returns (audio_bytes, meta).
    """
    text = _normalize_text(text)
    if not text:
        raise RuntimeError("Empty text for TTS.")

    c = _cfg()
    tried: list[str] = []

    # 1) Azure (if keys present)
    if c["AZURE_KEY"] and c["AZURE_REGION"]:
        tried.append("azure")
        try:
            return await _azure_synth_to_bytes(text, voice=voice)
        except Exception:
            pass  # fall through to Edge if enabled

    # 2) Edge (if enabled)
    if c["EDGE_ENABLED"]:
        tried.append("edge")
        try:
            return await _edge_synth_to_bytes(text, voice=voice, rate=rate, volume=volume)
        except Exception:
            pass

    raise RuntimeError(f"No TTS engine available (tried={tried}). "
                       f"Set AZURE_SPEECH_KEY/REGION or REYA_TTS_EDGE_ENABLED=1.")

# ----------------------- File helpers --------------------------------
async def synthesize_to_file(
    text: str,
    reya=None,
    out_path: str = "",
    voice_override: Optional[str] = None,
) -> str:
    text = _normalize_text(text)
    if not text:
        raise ValueError("Empty text for TTS.")
    if not out_path:
        raise ValueError("out_path is required.")

    voice = voice_override or (get_voice_and_preset(reya)[0] if reya else default_voice_for_text(text))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    audio, _meta = await synth_to_bytes(text, voice=voice)
    base, _ = os.path.splitext(out_path)
    final_path = f"{base}.mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp_mp3 = tmp.name
    try:
        with open(tmp_mp3, "wb") as f:
            f.write(audio)
        os.replace(tmp_mp3, final_path)
    finally:
        try:
            if os.path.exists(tmp_mp3):
                os.remove(tmp_mp3)
        except Exception:
            pass
    return final_path

async def synthesize_to_static_url(text: str, reya=None, voice_override: Optional[str] = None) -> str:
    name = f"{uuid4()}"
    mp3_path = AUDIO_DIR / f"{name}.mp3"
    final_fs = await synthesize_to_file(text, reya, str(mp3_path), voice_override=voice_override)
    rel = Path(final_fs).resolve().relative_to(STATIC_DIR.resolve()).as_posix()
    return f"/static/{rel}"

# ----------------------- Optional server-side playback ----------------
async def speak_with_voice_style_async(text: str, reya=None, voice_override: Optional[str] = None) -> None:
    text = _normalize_text(text)
    if not text:
        print("[TTS] Empty text, skipping playback.")
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp_path = tmp.name
    try:
        final_path = await synthesize_to_file(text, reya, tmp_path, voice_override=voice_override)
        if _PYDUB_OK:
            try:
                audio = AudioSegment.from_file(final_path, format="mp3")
                play(audio)
            except Exception as e:
                print(f"[TTS] Playback failed: {e}")
        else:
            print("[TTS] pydub/ffmpeg not available; skipping playback.")
    finally:
        try:
            if os.path.exists(tmp_path): os.remove(tmp_path)
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
