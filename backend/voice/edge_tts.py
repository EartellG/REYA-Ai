# backend/edge_tts.py
# Online Edge TTS first; if it fails (e.g., 401), fall back to local SAPI (pyttsx3) to WAV.
import os, re, asyncio, tempfile, io
from typing import Tuple, Dict, Any, Optional
from uuid import uuid4

# --- Primary online engine ---
import edge_tts

# --- Optional local playback (for speak_*), no need for ffmpeg if we skip playback ---
try:
    from pydub import AudioSegment
    from pydub.playback import play
    _PYDUB_OK = True
except Exception:
    _PYDUB_OK = False

# --- Local offline TTS fallback (Windows SAPI) ---
try:
    import pyttsx3  # saves WAV directly
    _PYTTSX3_OK = True
except Exception:
    _PYTTSX3_OK = False

STATIC_DIR = os.path.join("static")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# ---------------- Voice presets ----------------
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
    # kana/kanji → JP; otherwise CJK → Mandarin; else English
    jp_kana = any("\u3040" <= ch <= "\u30ff" for ch in text)
    cjk     = any("\u4e00" <= ch <= "\u9fff" for ch in text)
    if jp_kana:
        return "ja-JP-NanamiNeural"
    if cjk:
        return "zh-CN-XiaoxiaoNeural"
    return "en-US-JennyNeural"

# ---------------- Local WAV fallback ----------------
def _fallback_sapi_to_wav(text: str, out_path_wav: str) -> str:
    """
    Use pyttsx3 (Windows SAPI) to synthesize to WAV at out_path_wav.
    Tries to prefer an English UK female if available, otherwise default voice.
    """
    if not _PYTTSX3_OK:
        raise RuntimeError("pyttsx3 is not installed for local TTS fallback.")
    engine = pyttsx3.init()
    try:
        voices = engine.getProperty("voices") or []
        chosen = None
        for v in voices:
            name = (getattr(v, "name", "") or "").lower()
            langs = ",".join(getattr(v, "languages", []) or []).lower()
            if ("english" in name or "en" in langs) and ("gb" in name or "uk" in name or "gb" in langs or "uk" in langs):
                chosen = v.id
                break
        if chosen:
            engine.setProperty("voice", chosen)
    except Exception:
        pass
    engine.save_to_file(text, out_path_wav)
    engine.runAndWait()
    return out_path_wav

# ---------------- Public API ----------------
async def synthesize_to_file(
    text: str,
    reya=None,
    out_path: str = "",
    voice_override: Optional[str] = None,
) -> str:
    """
    Try Edge TTS first (MP3). If it fails (e.g., 401), fall back to local SAPI (WAV).
    Writes atomically: save to a temp file, fsync, then os.replace to the final path.
    Returns the final filesystem path ('.mp3' or '.wav').
    """
    text = _normalize_text(text)
    if not text:
        raise ValueError("Empty text for TTS.")
    if not out_path:
        raise ValueError("out_path is required.")

    # choose voice & preset
    if voice_override:
        voice = voice_override
        preset = {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"}
    else:
        base_voice, preset = get_voice_and_preset(reya)
        voice = base_voice or default_voice_for_text(text)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # helper for atomic replace
    def _atomic_replace(tmp_file: str, final_file: str) -> None:
        try:
            # ensure flushed to disk before swap
            with open(tmp_file, "rb") as f:
                os.fsync(f.fileno())
        except Exception:
            pass
        os.replace(tmp_file, final_file)

    # 1) Online (Edge TTS) -> MP3
    try:
        comm = edge_tts.Communicate(
            text,
            voice=voice,
            rate=preset.get("rate", "+0%"),
            pitch=preset.get("pitch", "+0Hz"),
            volume=preset.get("volume", "+0%"),
        )
        # save to temp first
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_mp3 = tmp.name
        try:
            await comm.save(tmp_mp3)
            _atomic_replace(tmp_mp3, out_path)
        finally:
            try:
                if os.path.exists(tmp_mp3):
                    os.remove(tmp_mp3)
            except Exception:
                pass
        return out_path  # MP3
    except Exception as e:
        # 2) Fallback: Local SAPI -> WAV (atomic)
        base, _ = os.path.splitext(out_path)
        final_wav = f"{base}.wav"
        if not _PYTTSX3_OK:
            raise RuntimeError(f"Edge TTS failed ({e}) and pyttsx3 not installed.") from e
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_wav = tmp.name
        try:
            _fallback_sapi_to_wav(text, tmp_wav)
            _atomic_replace(tmp_wav, final_wav)
        finally:
            try:
                if os.path.exists(tmp_wav):
                    os.remove(tmp_wav)
            except Exception:
                pass
        return final_wav

async def synthesize_to_static_url(
    text: str,
    reya=None,
    voice_override: Optional[str] = None
) -> str:
    """
    Save under static/audio/<uuid>.(mp3|wav) and return a URL path like
    /static/audio/<uuid>.(mp3|wav)
    """
    name = f"{uuid4()}"
    mp3_path = os.path.join(AUDIO_DIR, f"{name}.mp3")
    final_fs = await synthesize_to_file(text, reya, mp3_path, voice_override=voice_override)
    rel = os.path.relpath(final_fs, STATIC_DIR).replace("\\", "/")
    return f"/static/{rel}"

async def speak_with_voice_style_async(
    text: str,
    reya=None,
    voice_override: Optional[str] = None
) -> None:
    """
    Server-side local playback:
    - Uses synthesize_to_file to create an audio file (mp3 or wav)
    - Plays via pydub if available
    - Deletes temp file
    """
    text = _normalize_text(text)
    if not text:
        print("[TTS] Empty text, skipping playback.")
        return

    # synthesize to a temp file first (prefer mp3 name; may become wav)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp_path = tmp.name

    try:
        final_path = await synthesize_to_file(text, reya, tmp_path, voice_override=voice_override)
        if _PYDUB_OK:
            try:
                ext = os.path.splitext(final_path)[1].lstrip(".").lower() or "mp3"
                audio = AudioSegment.from_file(final_path, format=ext)
                play(audio)
            except Exception as e:
                print(f"[ERROR] Playback failed: {e}")
        else:
            print("[TTS] pydub/ffmpeg not available; skipping playback.")
    finally:
        try:
            if os.path.exists(tmp_path): os.remove(tmp_path)
            # if fallback produced .wav with a different name, also remove it
            wav_counterpart = os.path.splitext(tmp_path)[0] + ".wav"
            if os.path.exists(wav_counterpart): os.remove(wav_counterpart)
        except Exception:
            pass

def speak_with_voice_style(
    text: str,
    reya=None,
    voice_override: Optional[str] = None
) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        asyncio.create_task(
            speak_with_voice_style_async(text, reya, voice_override=voice_override)
        )
    else:
        asyncio.run(
            speak_with_voice_style_async(text, reya, voice_override=voice_override)
        )
