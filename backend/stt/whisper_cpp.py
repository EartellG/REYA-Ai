# backend/stt/whisper_cpp.py

import subprocess
import uuid
import os
from pathlib import Path

# BASE_DIR = backend/
BASE_DIR = Path(__file__).resolve().parent.parent

# Your folder is named literally "whisper.cpp"
WHISPER_DIR = BASE_DIR / "whisper.cpp"

WHISPER_EXE = WHISPER_DIR / "whisper-cli.exe"
MODEL_PATH = WHISPER_DIR / "models" / "ggml-large-v3-q5_0.bin"

# Where REYA stores transcription outputs
OUTPUT_DIR = BASE_DIR / "static" / "stt_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def transcribe_whisper_cpp(audio_path: str) -> str:
    """
    Transcribe audio using Whisper.cpp.
    Returns transcription text.
    """
    audio_path = str(Path(audio_path).resolve())  # ensure absolute path

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if not WHISPER_EXE.exists():
        raise FileNotFoundError(f"whisper-cli.exe not found at: {WHISPER_EXE}")

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found at: {MODEL_PATH}")

    # output basename for whisper
    out_base = OUTPUT_DIR / f"whisper_{uuid.uuid4().hex}"
    out_txt = Path(str(out_base) + ".txt")

    cmd = [
        str(WHISPER_EXE),
        "-m", str(MODEL_PATH),
        "-f", audio_path,
        "-l", "en",
        "-otxt",
        "-of", str(out_base)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(WHISPER_DIR)  # run inside whisper.cpp folder
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Whisper.cpp failed:\n"
                f"STDERR:\n{result.stderr}\n"
                f"STDOUT:\n{result.stdout}"
            )

        if not out_txt.exists():
            raise RuntimeError("Whisper output .txt file missing.")

        return out_txt.read_text(encoding="utf-8").strip()

    except Exception as e:
        raise RuntimeError(f"Whisper.cpp error: {e}")
