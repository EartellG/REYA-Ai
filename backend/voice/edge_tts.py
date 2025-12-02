# backend/voice/edge_tts.py
# Azure Speech first (preferred), optional Edge TTS fallback, and Silero offline fallback.
# Produces MP3 or WAV bytes under static/audio. No SAPI fallback.

import os, re, asyncio, tempfile
import torch
from typing import Tuple, Dict, Any, Optional
from uuid import uuid4
from pathlib import Path

# ----------------------- Optional dotenv loader -------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ----------------------- Project/static paths ---------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # backend/
STATIC_DIR   = PROJECT_ROOT / "static"
AUDIO_DIR    = STATIC_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------- Optional server-side playback ------------------
try:
    from pydub import AudioSegment
    from pydub.playback import play
    _PYDUB_OK = True
except Exception:
    _PYDUB_OK = False

# ----------------------- Runtime config (Auto-detect) -------------------
_engine_choice: Optional[str] = None  # cache best available engine


def _cfg() -> Dict[str, Any]:
    """Read environment and dynamically detect available engines."""
    global _engine_choice
    azure_key = os.getenv("AZURE_SPEECH_KEY") or ""
    azure_region = os.getenv("AZURE_SPEECH_REGION") or ""
    edge_enabled = os.getenv("REYA_TTS_EDGE_ENABLED", "0") == "1"
    forced_engine = os.getenv("REYA_TTS_ENGINE", "").lower().strip()

    # 🔍 Respect forced engine (silero, azure, or edge)
    if forced_engine in {"silero", "azure", "edge"}:
        _engine_choice = forced_engine
        print(f"[INIT] 🧩 Forcing TTS engine → {_engine_choice.upper()}")
    elif _engine_choice is None:
        if azure_key and azure_region:
            _engine_choice = "azure"
            print(f"[INIT] ✅ Azure TTS detected ({azure_region})")
        elif edge_enabled:
            _engine_choice = "edge"
            print("[INIT] ✅ Edge TTS enabled (fallback)")
        else:
            _engine_choice = "silero"
            print("[INIT] ✅ Using Silero (offline local TTS)")

    return {
        "AZURE_KEY": azure_key,
        "AZURE_REGION": azure_region,
        "EDGE_ENABLED": edge_enabled,
        "ENGINE_CHOICE": _engine_choice,
    }


def engine_status() -> Dict[str, Any]:
    """Return current detection info."""
    c = _cfg()
    return {
        "engine_choice": c["ENGINE_CHOICE"],
        "azure_present": bool(c["AZURE_KEY"] and c["AZURE_REGION"]),
        "region": c["AZURE_REGION"] or None,
        "edge_enabled": c["EDGE_ENABLED"],
    }


# ----------------------- Voices & text utils ----------------------------
def get_voice_and_preset(reya) -> Tuple[str, Dict[str, Any]]:
    style_to_voice = {
        "oracle":     "en-US-JennyNeural",
        "griot":      "en-US-AriaNeural",
        "cyberpunk":  "en-US-AmberNeural",
        "zen":        "en-GB-LibbyNeural",
        "detective":  "en-US-AnaNeural",
        "companion":  "en-GB-SoniaNeural",
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


# ----------------------- Azure helper -----------------------------------
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


# ----------------------- Edge helper (optional) -------------------------
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


# ----------------------- Preload Silero (cached) ------------------------
try:
    _silero_model, _silero_example, _silero_rate, _silero_speaker = torch.hub.load(
        'snakers4/silero-models', 'silero_tts', language='en', speaker='v3_en'
    ) # type: ignore
    print("[INIT] ✅ Silero model preloaded.")
except Exception as e:
    _silero_model = None
    print(f"[Silero] ⚠️ Preload failed: {e}")


# ----------------------- Public API (bytes) -----------------------------
async def synth_to_bytes(
    text: str,
    voice: str = "en-GB-SoniaNeural",
    rate: str = "+0%",
    volume: str = "+0%",
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Auto-select TTS engine: Azure → Edge → Silero.
    """
    text = _normalize_text(text)
    if not text:
        raise RuntimeError("Empty text for TTS.")

    c = _cfg()
    tried: list[str] = []
    engine_choice = c["ENGINE_CHOICE"]

    # Azure first
    if engine_choice == "azure":
        tried.append("azure")
        try:
            return await _azure_synth_to_bytes(text, voice=voice)
        except Exception as e:
            print(f"[WARN] Azure TTS failed → {e}")

    # Edge fallback
    if engine_choice in ("edge", "azure"):
        tried.append("edge")
        try:
            return await _edge_synth_to_bytes(text, voice=voice, rate=rate, volume=volume)
        except Exception as e:
            print(f"[WARN] Edge TTS failed → {e}")

    # Silero fallback
    tried.append("silero")
    try:
        if _silero_model:
            audio_path = os.path.join(tempfile.gettempdir(), f"reya_silero_{uuid4().hex}.wav")
            _silero_model.save_wav(text=text, speaker=_silero_speaker, sample_rate=_silero_rate, audio_path=audio_path)

            with open(audio_path, "rb") as f:
                data = f.read()
            return data, {"engine": "silero", "voice": _silero_speaker, "content_type": "audio/wav"}
        else:
            raise RuntimeError("Silero model not loaded.")
    except Exception as e:
        print(f"[Silero] Fallback failed: {e}")

    raise RuntimeError(f"No TTS engine available (tried={tried}).")


# ----------------------- File helpers ----------------------------------
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
    ext = ".wav" if _cfg()["ENGINE_CHOICE"] == "silero" else ".mp3"
    final_path = f"{base}{ext}"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp_path = tmp.name
    try:
        with open(tmp_path, "wb") as f:
            f.write(audio)
        os.replace(tmp_path, final_path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
    return final_path


async def synthesize_to_static_url(text: str, reya=None, voice_override: Optional[str] = None) -> str:
    name = f"{uuid4()}"
    ext = ".wav" if _cfg()["ENGINE_CHOICE"] == "silero" else ".mp3"
    file_path = AUDIO_DIR / f"{name}{ext}"
    final_fs = await synthesize_to_file(text, reya, str(file_path), voice_override=voice_override)
    rel = Path(final_fs).resolve().relative_to(STATIC_DIR.resolve()).as_posix()
    return f"/static/{rel}"


# ----------------------- Optional server-side playback -----------------
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
                audio = AudioSegment.from_file(final_path)
                play(audio)
            except Exception as e:
                print(f"[TTS] Playback failed: {e}")
        else:
            print("[TTS] pydub/ffmpeg not available; skipping playback.")
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
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
