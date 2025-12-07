# backend/stt/whisper_cpp.py
"""
Whisper.cpp helper wrapper.

Provides transcribe_whisper_cpp(audio_path, model_size="large", lang="en", task="transcribe", threads=4)

Expects whisper-cli executable at: <project-root>/backend/whisper.cpp/whisper-cli.exe
and model files under: <project-root>/backend/whisper.cpp/models/

Model selection:
 - "small"  -> tries to use models matching "ggml-small*.bin"
 - "large"  -> tries to use models matching "ggml-large*.bin" (large-v3 etc)
 - If exact filename provided via model_size (i.e. contains ".bin"), it will use that directly.

Notes:
 - This function is synchronous by design (good to call via asyncio.to_thread or run in a worker thread).
 - On failure it raises RuntimeError with CLI stderr/stdout included for diagnostics.
"""

from __future__ import annotations
import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional, List

# default base paths (adjusted to your project layout)
ROOT = Path(__file__).resolve().parent.parent  # backend/
WHISPER_CPP_DIR = ROOT / "whisper.cpp"
WHISPER_CLI = WHISPER_CPP_DIR / "whisper-cli.exe"
MODELS_DIR = WHISPER_CPP_DIR / "models"


def _find_whisper_cli() -> Optional[Path]:
    """Return path to whisper-cli.exe if present."""
    if WHISPER_CLI.exists():
        return WHISPER_CLI
    # try other common names if needed
    for alt in ("main.exe", "whisper.exe", "whisper_cli.exe"):
        p = WHISPER_CPP_DIR / alt
        if p.exists():
            return p
    return None


def _choose_model_file(model_size: str) -> Path:
    """
    Choose a model file based on requested model_size.
    Accepts:
      - "small"  -> picks ggml-small*.bin
      - "large"  -> picks ggml-large*.bin or ggml-large-v3*.bin
      - any filename ending with .bin will be treated as direct model filename
    Raises FileNotFoundError if no matching model found.
    """
    ms = (model_size or "").lower().strip()
    # direct file specified
    if ms.endswith(".bin"):
        p = MODELS_DIR / ms
        if p.exists():
            return p
        raise FileNotFoundError(f"Requested model file {p} does not exist.")

    # mapping keywords to patterns (order matters — prefer more specific)
    patterns = []
    if ms in ("small", "tiny", "sm"):
        patterns = ["ggml-small*.bin", "ggml-tiny*.bin"]
    elif ms in ("large", "v3", "large-v3"):
        patterns = ["ggml-large-v3*.bin", "ggml-large*.bin"]
    elif ms in ("base", "medium", "md"):
        patterns = ["ggml-base*.bin", "ggml-medium*.bin", "ggml-base-*"]
    else:
        # fallback: try small then large then base
        patterns = ["ggml-small*.bin", "ggml-large*.bin", "ggml-base*.bin"]

    # search models dir
    for pat in patterns:
        for p in MODELS_DIR.glob(pat):
            if p.is_file():
                return p

    # final fallback: any .bin in models dir
    candidates = sorted(MODELS_DIR.glob("*.bin"))
    if candidates:
        return candidates[-1]  # pick last (usually largest)
    raise FileNotFoundError(f"No model found for size '{model_size}' in {MODELS_DIR}")


def _build_cli_command(whisper_cli: Path, model: Path, audio_file: str, lang: str = "en", task: str = "transcribe", threads: int = 4) -> List[str]:
    """
    Construct command list for subprocess.run.
    Uses a conservative set of flags supported by most whisper.cpp builds.
    """
    # Base: whisper-cli.exe -m <model> -f <file> ...
    cmd = [str(whisper_cli)]
    # different builds may accept different flags; include the common ones
    cmd += ["-m", str(model)]
    cmd += ["-f", str(audio_file)]
    # threads
    cmd += ["-t", str(int(threads))]
    # language & task
    if lang:
        cmd += ["-l", str(lang)]
    if task:
        # some builds use --task, some use -otext etc. Use --task when available.
        cmd += ["--task", task]
    # request timestamps to be off by default for wake-word (makes parse simpler)
    # Do not add --no-timestamps universally; let caller request timestamps via task if desired.
    return cmd


def _parse_transcription_from_stdout(stdout: str) -> str:
    """
    Attempt to extract the transcription text from stdout.
    Different whisper.cpp builds have different formatting. Heuristics:
    - If stdout contains lines that look like "text:" or empty lines, pick the last chunk
    - Otherwise return entire stdout trimmed.
    """
    if not stdout:
        return ""

    # strip trailing noise lines
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    if not lines:
        return ""

    # heuristic: many builds print final transcription on last non-empty line
    # but sometimes there are numeric progress lines; choose last line that isn't "INFO:" style
    for ln in reversed(lines):
        # skip logs that look like "whisper_init..." or "main: processing"
        if ln.lower().startswith("whisper_") or ln.lower().startswith("main:") or ln.lower().startswith("stderr:") or ln.lower().startswith("std"):
            continue
        # skip pure numeric/progress lines
        if all(c.isdigit() or c in " .,-%()" for c in ln):
            continue
        # return the first plausible human text
        return ln

    # fallback
    return lines[-1]


def transcribe_whisper_cpp(audio_path: str, model_size: str = "large", lang: str = "en", task: str = "transcribe", threads: int = 4, timeout: Optional[int] = 60) -> str:
    """
    Transcribe `audio_path` using whisper.cpp's CLI.
    - audio_path: path to WAV/MP3 (string)
    - model_size: "small" | "large" | explicit filename (ggml-*.bin)
    - lang: language hint (e.g. "en")
    - task: "transcribe" or "translate"
    - threads: number of CPU threads to request
    - timeout: seconds for subprocess.run
    Returns the transcription string (may be empty).
    Raises RuntimeError on CLI errors with stdout/stderr included.
    """
    whisper_cli = _find_whisper_cli()
    if whisper_cli is None:
        raise RuntimeError(f"whisper-cli executable not found. Expected under: {WHISPER_CPP_DIR}. Please place whisper-cli.exe there.")

    # ensure audio file exists
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # choose model
    try:
        model_file = _choose_model_file(model_size)
    except FileNotFoundError as e:
        raise RuntimeError(f"Model selection failed: {e}")

    # build command
    cmd = _build_cli_command(whisper_cli, model_file, audio_path, lang=lang, task=task, threads=threads)

    # run CLI
    try:
        # ensure capturing both stdout and stderr
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"whisper-cli timed out after {timeout}s running: {' '.join(cmd)}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to run whisper-cli: {e}") from e

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    # If CLI returned non-zero, include stderr in error
    if proc.returncode != 0:
        # still try to parse stdout for clues
        parsed = _parse_transcription_from_stdout(stdout) or ""
        raise RuntimeError(f"Whisper.cpp failed (returncode={proc.returncode}). stdout: {parsed!r} stderr: {stderr!r}")

    # parse and return transcription
    parsed = _parse_transcription_from_stdout(stdout)
    return parsed


# small test helper if run directly
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test transcribe_whisper_cpp")
    parser.add_argument("audio", help="audio file to transcribe")
    parser.add_argument("--model", default="small", help="model size or filename (small|large|ggml-xx.bin)")
    parser.add_argument("--lang", default="en")
    args = parser.parse_args()
    try:
        text = transcribe_whisper_cpp(args.audio, model_size=args.model, lang=args.lang)
        print("TRANSCRIPTION:\n", text)
    except Exception as e:
        print("ERROR:", e)
