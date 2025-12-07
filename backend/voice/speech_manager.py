# backend/voice/speech_manager.py
"""
Unified speech manager.
FORCED XTTS VERSION — Silero disabled until XTTS is confirmed working.
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

# -------------------------------------------------------
# Try to import Coqui XTTS
# -------------------------------------------------------
try:
    from backend.voice.xtts_coqui import synthesize_xtts
    XTTS_AVAILABLE = True
    print("### DEBUG: XTTS import SUCCESS ###")
except Exception as e:
    synthesize_xtts = None
    XTTS_AVAILABLE = False
    logging.getLogger("uvicorn.error").warning(f"[TTS] XTTS NOT AVAILABLE: {e}")

# -------------------------------------------------------
# FORCE-DISABLE SILERO for now
# -------------------------------------------------------
synthesize_silero = None
SILERO_AVAILABLE = False


# -------------------------------------------------------
# Try to import simpleaudio for playback
# -------------------------------------------------------
try:
    import simpleaudio as sa
    SIMPLEAUDIO_AVAILABLE = True
except Exception:
    SIMPLEAUDIO_AVAILABLE = False


def play_local_wav(path: str, block: bool = False) -> None:
    """Play a local wav file using simpleaudio if available."""
    if not SIMPLEAUDIO_AVAILABLE:
        logging.getLogger("uvicorn.error").info(
            "[play_local_wav] simpleaudio not installed; skipping playback"
        )
        return
    try:
        wave_obj = sa.WaveObject.from_wave_file(path)
        play_obj = wave_obj.play()
        if block:
            play_obj.wait_done()
    except Exception as e:
        logging.getLogger("uvicorn.error").warning(f"[play_local_wav] playback failed: {e}")


# -------------------------------------------------------
# MAIN TTS FUNCTION — XTTS ONLY
# -------------------------------------------------------
def synthesize_tts(
    text: str,
    filename: Optional[str] = None,
    speaker: Optional[str] = None,
    language: Optional[str] = None,
) -> str:
    """
    Unified TTS entrypoint.
    *** XTTS is forced ON. Silero is ignored. ***
    """
    if not text or not text.strip():
        raise ValueError("Empty text passed to synthesize_tts")

    # Determine output file
    if filename:
        out_path = Path(filename)
        if not out_path.suffix:
            out_path = out_path.with_suffix(".wav")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path_str = str(out_path)
    else:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        out_path_str = tmp.name
        tmp.close()

    # ---------------------------------------------------
    # XTTS FORCED PRIMARY TTS
    # ---------------------------------------------------
    print("### DEBUG: Calling XTTS ###")
    if XTTS_AVAILABLE and synthesize_xtts is not None:
        try:
            result_path = synthesize_xtts(
                text=text,
                speaker=speaker,
                language=language,
                output_path=out_path_str
            )
            print(f"### DEBUG: XTTS returned file: {result_path} ###")
            return str(Path(result_path).resolve())
        except Exception as e:
            print("### XTTS FAILED ###")
            logging.getLogger("uvicorn.error").error(f"[TTS] XTTS synth failed: {e}")

    # ---------------------------------------------------
    # LAST RESORT — SILENT WAV  
    # ---------------------------------------------------
    print("### DEBUG: XTTS unavailable — creating silent WAV ###")
    try:
        import wave
        import struct
        framerate = 16000
        nframes = int(0.5 * framerate)
        with wave.open(out_path_str, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(framerate)
            for _ in range(nframes):
                wf.writeframes(struct.pack("<h", 0))
        return str(Path(out_path_str).resolve())
    except Exception as e:
        raise RuntimeError(f"[TTS] Could not produce fallback wav: {e}")


# -------------------------------------------------------
# RETURN BYTES WRAPPER
# -------------------------------------------------------
def synth_to_bytes(text: str, speaker: Optional[str] = None, language: Optional[str] = None) -> bytes:
    """Synthesizes to a temp wav and returns the raw bytes."""
    path = synthesize_tts(text, speaker=speaker, language=language)
    with open(path, "rb") as fh:
        return fh.read()


# -------------------------------------------------------
# STATIC FILE URL HELPER
# -------------------------------------------------------
def synthesize_to_static_url(
    text: str,
    reya_obj=None,
    speaker: Optional[str] = None,
    language: Optional[str] = None
) -> str:
    """Create static audio file for frontend."""
    audio_dir = Path(__file__).resolve().parent.parent / "static" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    filename = f"reya_{os.urandom(6).hex()}.wav"
    out_path = audio_dir / filename

    path = synthesize_tts(
        text,
        filename=str(out_path),
        speaker=speaker,
        language=language
    )

    return "/" + os.path.relpath(
        path,
        (Path(__file__).resolve().parent.parent / "static")
    ).replace("\\", "/")
