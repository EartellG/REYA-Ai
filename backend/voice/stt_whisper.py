# backend/voice/stt_whisper.py

import subprocess
from pathlib import Path

# Path to your Whisper.cpp Release folder
WHISPER_PATH = Path("C:/AI/Release")

# Your model file
MODEL = "ggml-large-v3-q5_0.bin"

def transcribe(audio_path: str) -> str:
    """Transcribe audio via whisper.cpp"""

    exe = WHISPER_PATH / "whisper-cli.exe"
    model_path = WHISPER_PATH / "models" / MODEL

    if not exe.exists():
        print(f"[Whisper] ERROR: Cannot find whisper-cli.exe at {exe}")
        return ""

    if not model_path.exists():
        print(f"[Whisper] ERROR: Cannot find model at {model_path}")
        return ""

    result = subprocess.run(
        [
            str(exe),
            "-m", str(model_path),
            "-f", audio_path,
            "-l", "en",
            "-otxt",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("[Whisper Error]:", result.stderr)
        return ""

    return result.stdout.strip()
