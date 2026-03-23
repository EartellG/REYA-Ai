# backend/stt/whisper_cpp.py
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, List

ROOT = Path(__file__).resolve().parent.parent  # backend/
WHISPER_CPP_DIR = ROOT / "whisper.cpp"
WHISPER_CLI = WHISPER_CPP_DIR / "whisper-cli.exe"
MODELS_DIR = WHISPER_CPP_DIR / "models"

ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
TIMESTAMP_RE = re.compile(
    r"^\[\s*\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\s*\]\s*(.*)$"
)


def _debug_enabled() -> bool:
    return os.getenv("REYA_WHISPER_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = ANSI_RE.sub("", text)
    text = text.replace("\x00", "")
    return text.strip()


def _find_whisper_cli() -> Optional[Path]:
    if WHISPER_CLI.exists():
        return WHISPER_CLI

    for alt in ("main.exe", "whisper.exe", "whisper_cli.exe"):
        p = WHISPER_CPP_DIR / alt
        if p.exists():
            return p

    return None


def _choose_model_file(model_size: str) -> Path:
    ms = (model_size or "").lower().strip()

    if ms.endswith(".bin"):
        p = MODELS_DIR / ms
        if p.exists():
            return p
        raise FileNotFoundError(f"Requested model file does not exist: {p}")

    patterns: List[str]
    if ms in ("small", "sm"):
        patterns = ["ggml-small*.bin", "ggml-base*.bin", "ggml-tiny*.bin"]
    elif ms in ("large", "v3", "large-v3"):
        patterns = ["ggml-large-v3*.bin", "ggml-large*.bin"]
    elif ms in ("base", "medium", "md"):
        patterns = ["ggml-base*.bin", "ggml-medium*.bin", "ggml-small*.bin"]
    else:
        patterns = ["ggml-small*.bin", "ggml-base*.bin", "ggml-large*.bin"]

    for pat in patterns:
        for p in MODELS_DIR.glob(pat):
            if p.is_file():
                return p

    candidates = sorted(MODELS_DIR.glob("*.bin"))
    if candidates:
        return candidates[-1]

    raise FileNotFoundError(f"No model found for size '{model_size}' in {MODELS_DIR}")


def _build_cli_command(
    whisper_cli: Path,
    model: Path,
    audio_file: str,
    lang: str = "en",
    task: str = "transcribe",
    threads: int = 4,
) -> List[str]:
    cmd = [
        str(whisper_cli),
        "-m", str(model),
        "-f", str(audio_file),
        "-t", str(int(threads)),
        "-l", str(lang or "en"),
        "-nt",
    ]

    # IMPORTANT:
    # This whisper-cli build does NOT support "--task".
    # Use "-tr" only when translation is explicitly requested.
    if (task or "").lower().strip() == "translate":
        cmd.append("-tr")

    return cmd


def _extract_plausible_lines(text: str) -> List[str]:
    text = _clean_text(text)
    if not text:
        return []

    out: List[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lower = line.lower()

        # HARD-REJECT obvious CLI errors/help output
        if lower.startswith("error:"):
            continue
        if lower.startswith("usage:"):
            continue
        if "unknown argument" in lower:
            continue
        if lower.startswith("options:"):
            continue
        if "supported audio formats:" in lower:
            continue
        if lower.startswith("voice activity detection"):
            continue

        m = TIMESTAMP_RE.match(line)
        if m:
            seg = m.group(1).strip()
            if seg:
                out.append(seg)
            continue

        # Skip common whisper/log lines
        if lower.startswith("whisper_"):
            continue
        if lower.startswith("main:"):
            continue
        if lower.startswith("system_info:"):
            continue
        if lower.startswith("processing"):
            continue
        if lower.startswith("output_"):
            continue
        if lower.startswith("bench"):
            continue

        out.append(line)

    return out


def _stderr_has_cli_error(stderr: str) -> bool:
    s = _clean_text(stderr).lower()
    return (
        "unknown argument" in s
        or s.startswith("error:")
        or "usage:" in s
    )


def _parse_transcription(stdout: str, stderr: str) -> str:
    stdout_lines = _extract_plausible_lines(stdout)
    if stdout_lines:
        return " ".join(stdout_lines).strip()

    stderr_lines = _extract_plausible_lines(stderr)
    if stderr_lines:
        return " ".join(stderr_lines).strip()

    return ""


def transcribe_whisper_cpp(
    audio_path: str,
    model_size: str = "large",
    lang: str = "en",
    task: str = "transcribe",
    threads: int = 4,
    timeout: Optional[int] = 60,
) -> str:
    whisper_cli = _find_whisper_cli()
    if whisper_cli is None:
        raise RuntimeError(f"whisper-cli executable not found under: {WHISPER_CPP_DIR}")

    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    model_file = _choose_model_file(model_size)

    cmd = _build_cli_command(
        whisper_cli=whisper_cli,
        model=model_file,
        audio_file=str(audio_file),
        lang=lang,
        task=task,
        threads=threads,
    )

    if _debug_enabled():
        print(f"[Whisper DEBUG] cmd: {' '.join(cmd)}")
        print(f"[Whisper DEBUG] audio: {audio_file}")
        print(f"[Whisper DEBUG] model: {model_file}")

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            cwd=str(WHISPER_CPP_DIR),
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"whisper-cli timed out after {timeout}s") from e
    except Exception as e:
        raise RuntimeError(f"Failed to run whisper-cli: {e}") from e

    stdout = _clean_text(proc.stdout or "")
    stderr = _clean_text(proc.stderr or "")

    if _debug_enabled():
        print(f"[Whisper DEBUG] returncode={proc.returncode}")
        print(f"[Whisper DEBUG] stdout:\n{stdout}")
        print(f"[Whisper DEBUG] stderr:\n{stderr}")

    # Some whisper builds return 0 even when stderr contains a CLI usage error.
    if proc.returncode != 0 or _stderr_has_cli_error(stderr):
        raise RuntimeError(
            f"Whisper.cpp CLI error. returncode={proc.returncode} stdout={stdout!r} stderr={stderr!r}"
        )

    parsed = _parse_transcription(stdout, stderr)
    if parsed:
        return parsed

    return ""