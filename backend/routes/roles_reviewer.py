# backend/routes/roles_reviewer.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Tuple
from pathlib import Path
import asyncio
import json
import shutil
import sys
import os

router = APIRouter(prefix="/roles/reviewer", tags=["roles-reviewer"])

# -------- One-shot prefill buffer (Coder -> Reviewer handoff) --------
_PREFILL: Optional[dict] = None

@router.get("/prefill")
def get_prefill():
    """
    One-shot prefill fetch for ReviewerPanel. Returns {"prefill": None} if empty.
    After a successful read, the buffer is cleared.
    """
    global _PREFILL
    if not _PREFILL:
        return {"prefill": None}
    buf = _PREFILL
    _PREFILL = None
    return {"prefill": buf}

@router.post("/prefill")
def set_prefill(payload: dict):
    """
    Allow Coder (or any upstream tool) to stage files/issues for Reviewer.
    Expected shape (flexible):
      {
        "ticket": {...},                # optional
        "files": [{"path","contents"}], # optional
        "notes": "string",              # optional
      }
    """
    global _PREFILL
    _PREFILL = payload or {}
    return {"ok": True}


# ---------------- Models for review ----------------
class FilePatch(BaseModel):
    path: str
    contents: str

class ReviewRequest(BaseModel):
    files: List[FilePatch]

class ReviewFinding(BaseModel):
    path: str
    notes: List[str]

class ReviewReply(BaseModel):
    summary: str
    findings: List[ReviewFinding]

class FileBlob(BaseModel):
    path: str
    contents: str

class ReviewIssue(BaseModel):
    id: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    col: Optional[int] = None
    severity: Literal["error", "warning", "info"] = "warning"
    message: str
    suggestion: Optional[str] = None
    rule: Optional[str] = None
    source: Optional[str] = None

class LintRequest(BaseModel):
    files: List[FileBlob]

class LintReply(BaseModel):
    summary: str
    issues: List[ReviewIssue]


# ---------------- Simple review endpoint (lightweight heuristic) ----------------
@router.post("/review", response_model=ReviewReply)
async def review(req: ReviewRequest):
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")
    findings: List[ReviewFinding] = []
    for f in req.files:
        notes = []
        if "console.log" in f.contents:
            notes.append("Avoid console.log in committed code.")
        if " any " in f.contents or f.contents.strip().startswith("any"):
            notes.append("TypeScript: reduce 'any' usage if possible.")
        if "TODO" in f.contents or "FIXME" in f.contents:
            notes.append("Resolve TODO/FIXME before merging.")
        if notes:
            findings.append(ReviewFinding(path=f.path, notes=notes))
    return ReviewReply(
        summary=f"Reviewed {len(req.files)} file(s). {len(findings)} with notes.",
        findings=findings
    )


# ---------------- Tool discovery helpers ----------------
def _eslint_available() -> bool:
    # Prefer npx (project-local eslint), fallback to global eslint if present.
    return bool(shutil.which("npx") or shutil.which("eslint") or shutil.which("eslint.cmd"))

def _ruff_cmd() -> Optional[List[str]]:
    # Prefer ruff binary; else python -m ruff using active interpreter
    if shutil.which("ruff") or shutil.which("ruff.exe"):
        return ["ruff"]
    if sys.executable:
        return [sys.executable, "-m", "ruff"]
    return None

def _is_js_like(path: str) -> bool:
    p = path.lower()
    return p.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"))

def _is_py(path: str) -> bool:
    return path.lower().endswith(".py")

@router.get("/lint/health")
def lint_health():
    return {
        "ok": True,
        "tools": {
            "npx": bool(shutil.which("npx")),
            "eslint": bool(shutil.which("eslint") or shutil.which("eslint.cmd")),
            "ruff": bool(shutil.which("ruff") or shutil.which("ruff.exe")) or bool(sys.executable),
            "python": sys.executable,
        },
    }


# ---------------- Async subprocess helpers (non-blocking) ----------------
async def _run_proc(cmd: List[str], input_text: Optional[str] = None, cwd: Optional[Path] = None, timeout: int = 30) -> Tuple[int, str, str]:
    """
    Run a command asynchronously with optional stdin and timeout.
    Returns: (returncode, stdout, stderr)
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE if input_text is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=input_text.encode("utf-8") if input_text is not None else None),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return (124, "", f"Timed out running: {' '.join(cmd)}")
    return (proc.returncode, stdout.decode("utf-8", errors="ignore"), stderr.decode("utf-8", errors="ignore"))


# ---------------- ESLint / Ruff runners (stdin mode, per-file) ----------------
async def _run_eslint_stdin(file: FileBlob) -> List[ReviewIssue]:
    """
    Run ESLint against a single file via stdin (no filesystem writes).
    Uses npx when available to honor project-local eslint config.
    """
    if not _eslint_available() or not _is_js_like(file.path):
        return []

    # Prefer npx for local eslint, else fallback to global eslint.
    if shutil.which("npx"):
        cmd = ["npx", "eslint", "--stdin", "--stdin-filename", file.path, "-f", "json"]
    else:
        # global eslint
        eslint = shutil.which("eslint") or shutil.which("eslint.cmd")
        cmd = [eslint, "--stdin", "--stdin-filename", file.path, "-f", "json"] if eslint else []

    if not cmd:
        return []

    rc, out, _err = await _run_proc(cmd, input_text=file.contents, timeout=45)
    # ESLint exits 0 (no issues) or 1 (issues). Other codes mean failure.
    if rc not in (0, 1):
        return []

    issues: List[ReviewIssue] = []
    try:
        payload = json.loads(out or "[]")
        # payload is an array with one result object for stdin
        for file_res in payload:
            file_path = file_res.get("filePath", file.path)
            for m in file_res.get("messages", []):
                rule = (m.get("ruleId") or "-") if isinstance(m, dict) else "-"
                sev = "error" if m.get("severity", 1) == 2 else "warning"
                issues.append(ReviewIssue(
                    file=Path(file_path).as_posix(),
                    line=m.get("line"),
                    col=m.get("column"),
                    severity=sev,
                    rule=rule,
                    message=m.get("message") or "",
                    source="eslint",
                ))
    except json.JSONDecodeError:
        pass
    return issues

async def _run_ruff_stdin(file: FileBlob) -> List[ReviewIssue]:
    """
    Run Ruff against a single file via stdin. Requires ruff or python -m ruff.
    """
    if not _is_py(file.path):
        return []

    rcmd = _ruff_cmd()
    if not rcmd:
        return []

    # Ruff: read from stdin ('-') and supply --stdin-filename for proper rule selection
    cmd = [*rcmd, "check", "-", "--format", "json", "--stdin-filename", file.path]
    rc, out, _err = await _run_proc(cmd, input_text=file.contents, timeout=45)

    issues: List[ReviewIssue] = []
    if not out:
        return issues

    try:
        ruff_json = json.loads(out)
        # JSON is a list of diagnostics
        for entry in ruff_json:
            loc = entry.get("location") or {}
            issues.append(ReviewIssue(
                file=Path(entry.get("filename", file.path)).as_posix(),
                line=loc.get("row"),
                col=loc.get("column"),
                severity="warning" if entry.get("type") == "warning" else "error",
                rule=entry.get("code"),
                message=entry.get("message") or "",
                source="ruff",
            ))
    except json.JSONDecodeError:
        pass
    return issues


def _inline_fallback_scan(files: List[FileBlob]) -> List[ReviewIssue]:
    """Very small safety net so the UI never returns empty."""
    issues: List[ReviewIssue] = []
    for f in files:
        lines = f.contents.splitlines()
        for i, line in enumerate(lines, start=1):
            if "console.log(" in line:
                issues.append(ReviewIssue(
                    file=f.path, line=i, col=max(line.find("console.log("), 0) + 1,
                    severity="warning", message="Avoid console.log in committed code.",
                    rule="no-console", source="inline"
                ))
            if "TODO" in line or "FIXME" in line:
                issues.append(ReviewIssue(
                    file=f.path, line=i, col=1,
                    severity="info", message="Resolve TODO/FIXME before merging.",
                    rule="todo-comment", source="inline"
                ))
    return issues


# ---------------- Lint endpoint (async, non-blocking) ----------------
@router.post("/lint", response_model=LintReply)
async def lint(req: LintRequest):
    """
    Real lint runner (non-blocking):
      - Runs ESLint (JS/TS/TSX) via stdin per file, JSON output
      - Runs Ruff (Python) via stdin per file, JSON output
      - Normalizes into ReviewIssue[]
    Falls back to a tiny inline scan if no external tools found or output empty.
    NOTE: No .diff files are ever created; JSON issues only.
    """
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    # Kick off all applicable linters concurrently (per file).
    eslint_tasks = [asyncio.create_task(_run_eslint_stdin(f)) for f in req.files if _is_js_like(f.path)]
    ruff_tasks   = [asyncio.create_task(_run_ruff_stdin(f))   for f in req.files if _is_py(f.path)]

    issues: List[ReviewIssue] = []

    if eslint_tasks:
        eslint_groups = await asyncio.gather(*eslint_tasks, return_exceptions=True)
        for res in eslint_groups:
            if isinstance(res, Exception):
                continue
            issues.extend(res)

    if ruff_tasks:
        ruff_groups = await asyncio.gather(*ruff_tasks, return_exceptions=True)
        for res in ruff_groups:
            if isinstance(res, Exception):
                continue
            issues.extend(res)

    # Fallback inline scan so the UI isn't empty
    if not issues:
        issues = _inline_fallback_scan(req.files)

    return LintReply(
        summary=f"Linted {len(req.files)} file(s). Found {len(issues)} issue(s).",
        issues=issues
    )
