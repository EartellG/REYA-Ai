import subprocess
import tempfile
import os
from pathlib import Path

WHISPER_PATH = Path("C:/Users/Sydne.YAYU/whisper.cpp")
MODEL = "ggml-base.en.bin"

def transcribe(audio_path: str) -> str:
    """Transcribe audio via whisper.cpp"""
    result = subprocess.run(
        [
            str(WHISPER_PATH / "main.exe"),
            "-m", str(WHISPER_PATH / "models" / MODEL),
            "-f", audio_path,
            "--language", "en",
            "--output-txt",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("[Whisper] Error:", result.stderr)
        return ""
    return result.stdout.strip()
