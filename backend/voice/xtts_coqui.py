# backend/voice/xtts_coqui.py
"""
Coqui XTTS v2 wrapper with a small static-file helper and engine_status.
Designed to fail gracefully and provide helpful diagnostics.
"""
import os
import tempfile
import traceback
from pathlib import Path
from typing import Optional

# Try import TTS; fail gracefully
try:
    from TTS.api import TTS  # type: ignore # coqui TTS
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

# default model identifier (user can override with COQUI_MODEL env var)
DEFAULT_MODEL = os.getenv("COQUI_MODEL", "")  # e.g. "tts_models/multilingual/multi-dataset/xtts_v2"
# Respect optional GPU env flag
_USE_GPU = os.getenv("REYA_TTS_USE_GPU", "0") in ("1", "true", "True", "yes", "YES")

# cache loaded TTS instance
_tts_instance = None
_tts_model_name = None


def _get_tts_instance(preferred_model: Optional[str] = None):
    """
    Load and cache a TTS instance. Will raise RuntimeError with helpful diagnostics if TTS isn't available.
    """
    global _tts_instance, _tts_model_name

    if not TTS_AVAILABLE:
        raise RuntimeError("Coqui TTS (TTS.api) not available. Install with: python -m pip install TTS")

    model = preferred_model or DEFAULT_MODEL or None

    if _tts_instance and (model is None or _tts_model_name == model):
        return _tts_instance

    try:
        # always pass gpu flag explicitly (TTS expects boolean for 'gpu' param)
        gpu_flag = bool(_USE_GPU)
        if model:
            print(f"[XTTS] Loading model: {model} (gpu={gpu_flag})")
            _tts_instance = TTS(model_name=model, progress_bar=False, gpu=gpu_flag)
            _tts_model_name = model
            return _tts_instance
        else:
            # attempt a few candidate model names (non-exhaustive)
            candidates = [
                "tts_models/multilingual/multi-dataset/xtts_v2",
                "tts_models/multilingual/multi-dataset/xtts_v1.1",
                "tts_models/multilingual/multi-dataset/your_tts",
            ]
            for cand in candidates:
                try:
                    print(f"[XTTS] Trying candidate model: {cand}")
                    _tts_instance = TTS(model_name=cand, progress_bar=False, gpu=gpu_flag)
                    _tts_model_name = cand
                    print(f"[XTTS] Loaded candidate model {cand}")
                    return _tts_instance
                except Exception as e:
                    print(f"[XTTS] candidate {cand} failed: {e}")
            # last resort: autodiscover
            print("[XTTS] Attempting TTS() autodiscover")
            _tts_instance = TTS(progress_bar=False, gpu=gpu_flag)
            _tts_model_name = getattr(_tts_instance, "model_name", None)
            return _tts_instance

    except Exception as e:
        raise RuntimeError(f"Failed to load Coqui TTS model '{model}': {e}\n{traceback.format_exc()}")


def synthesize_xtts(
    text: str,
    speaker: Optional[str] = None,
    language: Optional[str] = None,
    output_path: Optional[str] = None,
    use_gpu: Optional[bool] = None,
) -> str:
    """
    Synthesize `text` using Coqui XTTS. Returns a local .wav path.
    """
    if not text or not text.strip():
        raise ValueError("Empty text passed to synthesize_xtts")

    if not TTS_AVAILABLE:
        raise RuntimeError("Coqui TTS library not installed (pip install TTS)")

    # prefer argument use_gpu over environment flag
    if use_gpu is None:
        use_gpu = _USE_GPU

    tts = _get_tts_instance(preferred_model=None)

    # prepare output path
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out_path = str(out)
    else:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        out_path = tmp.name
        tmp.close()

    # pass model kwargs — speaker and language largely depend on model support
    kwargs = {}
    if speaker:
        kwargs["speaker"] = speaker
    if language:
        kwargs["language"] = language

    try:
        if hasattr(tts, "tts_to_file"):
            # new style API
            tts.tts_to_file(text=text, file_path=out_path, **kwargs)
        elif hasattr(tts, "tts"):
            audio, sr = tts.tts(text=text, **kwargs)
            import soundfile as sf
            sf.write(out_path, audio, sr)
        else:
            raise RuntimeError("TTS instance does not expose tts methods")
        print(f"[XTTS] Wrote synthesis to {out_path}")
        return out_path
    except Exception as e:
        raise RuntimeError(f"XTTS synth failed: {e}\n{traceback.format_exc()}")


def synthesize_xtts_to_static_url(
    text: str,
    speaker: Optional[str] = None,
    language: Optional[str] = None,
    out_dir: Optional[str] = None,
) -> Optional[str]:
    """
    Synthesize text and put the .wav into project static/audio folder (so your web server can serve it).
    Returns a relative URL like '/audio/<file>.wav' (works with FastAPI mount /static).
    """
    try:
        # default out_dir is backend/static/audio (two levels up from this file)
        base = Path(__file__).resolve().parent.parent  # backend/
        static_audio = base / "static" / "audio"
        if out_dir:
            static_audio = Path(out_dir)
        static_audio.mkdir(parents=True, exist_ok=True)

        filename = f"reya_{os.urandom(6).hex()}.wav"
        out_path = static_audio / filename
        path = synthesize_xtts(text, speaker=speaker, language=language, output_path=str(out_path))
        # return URL relative to static mount; if your app mounts /static at project/static, adjust accordingly.
        rel = "/" + os.path.relpath(path, base / "static").replace("\\", "/")
        return rel
    except Exception as e:
        # bubble helpful message to caller (do not crash global import)
        raise RuntimeError(f"synthesize_xtts_to_static_url failed: {e}\n{traceback.format_exc()}")


def engine_status() -> dict:
    """
    Return small diagnostics for the current XTTS engine state.
    """
    return {
        "engine": "coqui_xtts",
        "DEFAULT_MODEL": DEFAULT_MODEL,
        "TTS_AVAILABLE": TTS_AVAILABLE,
        "loaded_model": _tts_model_name,
        "use_gpu_env": _USE_GPU,
    }
