"""
Unified speech manager.
Forced XTTS — Silero disabled.
"""

import logging
import tempfile
import re
import wave
import struct
from pathlib import Path
from typing import Optional

# ---------------------------
# Import XTTS
# ---------------------------
try:
    from backend.voice.xtts_coqui import synthesize_xtts
    XTTS_AVAILABLE = True
    print("### DEBUG: XTTS import SUCCESS ###")
except Exception as e:
    synthesize_xtts = None
    XTTS_AVAILABLE = False
    logging.getLogger("uvicorn.error").warning(f"[TTS] XTTS NOT AVAILABLE: {e}")

# Disable Silero permanently
synthesize_silero = None
SILERO_AVAILABLE = False

# Optional playback
try:
    import simpleaudio as sa
    SIMPLEAUDIO_AVAILABLE = True
except Exception:
    SIMPLEAUDIO_AVAILABLE = False


# ---------------------------
# Play wav locally (optional)
# ---------------------------
def play_local_wav(path: str, block: bool = False):
    if not SIMPLEAUDIO_AVAILABLE:
        return
    try:
        obj = sa.WaveObject.from_wave_file(path)  # type: ignore
        play = obj.play()
        if block:
            play.wait_done()
    except Exception as e:
        logging.getLogger("uvicorn.error").warning(f"[play_local_wav] failed: {e}")


# ---------------------------
# Chunk text helper (XTTS-safe)
# ---------------------------
def chunk_text(text: str, max_chars: int = 230) -> list[str]:
    """
    Split text into sentence-aware chunks safe for XTTS.
    """
    if not text:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks: list[str] = []
    buf = ""

    for s in sentences:
        if len(buf) + len(s) <= max_chars:
            buf += (" " if buf else "") + s
        else:
            if buf:
                chunks.append(buf)
            buf = s

    if buf:
        chunks.append(buf)

    return chunks


# ---------------------------
# Main TTS entrypoint
# ---------------------------
def synthesize_tts(
    text: str,
    filename: Optional[str] = None,
    speaker: Optional[str] = None,
    language: Optional[str] = None,
) -> str:

    if not text or not text.strip():
        raise ValueError("Empty text for synthesize_tts")

    # Determine output path
    if filename:
        out = Path(filename)
        out.parent.mkdir(parents=True, exist_ok=True)
        out_path = str(out)
    else:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        out_path = tmp.name
        tmp.close()

    # ---------------------------
    # XTTS PRIMARY ENGINE (chunked)
    # ---------------------------
    print("### DEBUG: Calling XTTS ###")
    if XTTS_AVAILABLE and synthesize_xtts:
        try:
            chunks = chunk_text(text)
            wav_parts: list[str] = []

            for i, chunk in enumerate(chunks):
                part_path = str(
                    Path(out_path).with_stem(f"{Path(out_path).stem}_{i}")
                )

                result = synthesize_xtts(
                    text=chunk,
                    language=language or "en",
                    output_path=part_path,
                )

                if result:
                    wav_parts.append(result)

            # Merge WAV chunks
            if wav_parts:
                with wave.open(out_path, "wb") as wf_out:
                    first = True
                    for p in wav_parts:
                        with wave.open(p, "rb") as wf_in:
                            if first:
                                wf_out.setnchannels(wf_in.getnchannels())
                                wf_out.setsampwidth(wf_in.getsampwidth())
                                wf_out.setframerate(wf_in.getframerate())
                                first = False
                            wf_out.writeframes(
                                wf_in.readframes(wf_in.getnframes())
                            )

                return str(Path(out_path).resolve())

        except Exception as e:
            logging.getLogger("uvicorn.error").error(f"[TTS] XTTS failed: {e}")

    # ---------------------------
    # FALLBACK → Silent wav
    # ---------------------------
    print("### DEBUG: XTTS unavailable — creating silent WAV ###")
    fr = 16000
    frames = int(0.5 * fr)

    with wave.open(out_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(fr)
        for _ in range(frames):
            wf.writeframes(struct.pack("<h", 0))

    return str(Path(out_path).resolve())


# ---------------------------
# Bytes wrapper
# ---------------------------
def synth_to_bytes(text: str, speaker=None, language=None) -> bytes:
    path = synthesize_tts(text, speaker=speaker, language=language)
    return Path(path).read_bytes()


# ---------------------------
# Static URL generator
# ---------------------------
def synthesize_to_static_url(
    text: str,
    reya_obj=None,
    speaker: Optional[str] = None,
    language: Optional[str] = None,
):
    audio_dir = Path(__file__).resolve().parent.parent / "static" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    filename = f"reya_{os.urandom(6).hex()}.wav"
    out_path = audio_dir / filename

    synthesize_tts(
        text=text,
        filename=str(out_path),
        speaker=speaker,
        language=language,
    )

    return "/" + out_path.relative_to(audio_dir.parent).as_posix()
