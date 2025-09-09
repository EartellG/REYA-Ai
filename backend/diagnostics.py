# backend/diagnostics.py
import os
import shutil
import tempfile
import asyncio
from dataclasses import dataclass
from typing import List, Optional

# Optional deps
try:
    import httpx
    _HTTPX_OK = True
except Exception:
    _HTTPX_OK = False

try:
    import torch
    _TORCH_OK = True
except Exception:
    _TORCH_OK = False

from backend.llm_interface import (
    get_structured_reasoning_prompt,
    query_ollama,
    get_installed_models,   # <<< fallback via CLI
    get_default_model,      # <<< use your configured default
)
from backend.voice.edge_tts import synthesize_to_file

@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    warn: bool = False

@dataclass
class DiagnosticsReport:
    checks: List[CheckResult]
    summary: str

    def as_text(self) -> str:
        lines = ["REYA Diagnostics Report", "=======================", ""]
        for c in self.checks:
            icon = "✅" if c.ok else ("⚠️" if c.warn else "❌")
            lines.append(f"{icon} {c.name}")
            if c.detail:
                lines.append(f"   ↳ {c.detail}")
        lines.append("")
        lines.append(f"Summary: {self.summary}")
        return "\n".join(lines)

async def _check_personality(reya) -> CheckResult:
    try:
        assert reya is not None, "reya is None"
        return CheckResult("Personality loaded", True, f"style={reya.style}, traits={len(reya.traits)}")
    except Exception as e:
        return CheckResult("Personality loaded", False, str(e))

async def _check_memory(memory) -> CheckResult:
    try:
        ctx_before = memory.get_context()
        memory.remember("diag:key", "diag:value")
        ctx_after = memory.get_context()
        changed = ctx_before != ctx_after or "diag:key" in str(ctx_after)
        return CheckResult("Memory read/write", changed, "context changed" if changed else "context unchanged")
    except Exception as e:
        return CheckResult("Memory read/write", False, str(e))

async def _check_llm(reya, memory) -> CheckResult:
    try:
        prompt = get_structured_reasoning_prompt("diagnostics probe", memory.get_context(), reya=reya)
        resp = await asyncio.to_thread(query_ollama, prompt)
        ok = isinstance(resp, str) and len(resp.strip()) > 0
        return CheckResult("LLM response (Ollama)", ok, f"len={len(resp)}" if ok else "empty response")
    except Exception as e:
        return CheckResult("LLM response (Ollama)", False, str(e))

async def _check_tts(reya) -> CheckResult:
    try:
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "diag.mp3")
            await synthesize_to_file("Diagnostics voice check.", reya, out)
            ok = os.path.exists(out) and os.path.getsize(out) > 0
            return CheckResult("TTS pipeline (edge_tts)", ok, "mp3 created" if ok else "no file")
    except Exception as e:
        return CheckResult("TTS pipeline (edge_tts)", False, str(e))

async def _check_disk_space(min_free_mb: int = 50) -> CheckResult:
    try:
        total, used, free = shutil.disk_usage(".")
        free_mb = int(free / (1024 * 1024))
        ok = free_mb >= min_free_mb
        return CheckResult("Disk space", ok, f"free={free_mb}MB (min {min_free_mb}MB)", warn=not ok)
    except Exception as e:
        return CheckResult("Disk space", False, str(e))

async def _check_ollama_models(expected: Optional[str]) -> CheckResult:
    """
    Try HTTP API first; if unavailable or empty, fall back to CLI list
    via llm_interface.get_installed_models().
    """
    models: List[str] = []
    detail_parts: List[str] = []

    # HTTP route (if httpx installed)
    if _HTTPX_OK:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get("http://127.0.0.1:11434/api/tags")
                if r.status_code == 200:
                    data = r.json()
                    http_models = [m.get("name", "") for m in data.get("models", [])]
                    if http_models:
                        models = http_models
                        detail_parts.append(f"http ok ({len(models)} models)")
                else:
                    detail_parts.append(f"http status={r.status_code}")
        except Exception as e:
            detail_parts.append(f"http err={e}")

    # Fallback to CLI if HTTP yielded nothing
    if not models:
        try:
            cli_models = get_installed_models()
            if cli_models:
                models = cli_models
                detail_parts.append(f"cli ok ({len(models)} models)")
            else:
                detail_parts.append("cli empty")
        except Exception as e:
            detail_parts.append(f"cli err={e}")

    ok_any = len(models) > 0
    models_str = ", ".join(models) if models else "none"
    detail_parts.append(f"installed=[{models_str}]")

    if expected:
        has = any(expected in m for m in models)
        detail_parts.append(f"required='{expected}'")
        return CheckResult(
            "Ollama models",
            ok_any and has,
            "; ".join(detail_parts) + ("" if has else "; missing required"),
            warn=ok_any and not has
        )

    return CheckResult("Ollama models", ok_any, "; ".join(detail_parts))

async def _check_gpu() -> CheckResult:
    if not _TORCH_OK:
        return CheckResult("GPU (PyTorch)", False, "torch not installed", warn=True)
    try:
        cuda_ok = torch.cuda.is_available()
        return CheckResult("GPU (PyTorch)", cuda_ok, "CUDA available" if cuda_ok else "CUDA not available", warn=not cuda_ok)
    except Exception as e:
        return CheckResult("GPU (PyTorch)", False, str(e), warn=True)

async def run_diagnostics(reya, memory, *, expected_ollama_model: Optional[str] = None) -> DiagnosticsReport:
    # Auto-detect the configured default model if not provided
    expected = expected_ollama_model or get_default_model()

    checks = await asyncio.gather(
        _check_personality(reya),
        _check_memory(memory),
        _check_llm(reya, memory),
        _check_tts(reya),
        _check_disk_space(50),
        _check_ollama_models(expected),
        _check_gpu(),
    )
    passed = sum(1 for c in checks if c.ok)
    total = len(checks)
    return DiagnosticsReport(checks=list(checks), summary=f"{passed}/{total} checks passed")
