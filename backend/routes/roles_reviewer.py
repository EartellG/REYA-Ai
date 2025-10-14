# backend/routes/roles_reviewer.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict
from pathlib import Path
import tempfile
import json
import subprocess
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


# ---------------- Simple review endpoint ----------------
@router.post("/review", response_model=ReviewReply)
async def review(req: ReviewRequest):
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")
    findings: List[ReviewFinding] = []
    for f in req.files:
        notes = []
        if "console.log" in f.contents:
            notes.append("Avoid console.log in committed code.")
        if "any" in f.contents:
            notes.append("TypeScript: reduce 'any' usage if possible.")
        if "TODO" in f.contents or "FIXME" in f.contents:
            notes.append("Resolve TODO/FIXME before merging.")
        if notes:
            findings.append(ReviewFinding(path=f.path, notes=notes))
    return ReviewReply(
        summary=f"Reviewed {len(req.files)} file(s). {len(findings)} with notes.",
        findings=findings
    )


# ---------------- ESLint / Ruff integration ----------------
def _run(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, shell=False)

def _ensure_files(tmp: Path, files: List[FileBlob]) -> None:
    for f in files:
        p = tmp / f.path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f.contents, encoding="utf-8")

def _eslint_exists() -> bool:
    # We will call via npx; ensure either eslint or npx is present
    return bool(shutil.which("eslint") or shutil.which("eslint.cmd") or shutil.which("npx"))

def _ruff_cmd() -> Optional[List[str]]:
    # Prefer a ruff binary, else python -m ruff using the active interpreter
    if shutil.which("ruff") or shutil.which("ruff.exe"):
        return ["ruff"]
    return [sys.executable, "-m", "ruff"] if sys.executable else None

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

@router.post("/lint", response_model=LintReply)
def lint(req: LintRequest):
    """
    Real lint runner:
      - Writes provided files to a temp dir
      - Runs ESLint (via npx) with JSON formatter
      - Runs Ruff (binary or python -m ruff) with JSON output
      - Normalizes into ReviewIssue[]
    Falls back to a tiny inline scan if no external tools found.
    """
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    issues: List[ReviewIssue] = []

    with tempfile.TemporaryDirectory(prefix="reya_lint_") as td:
        tmp = Path(td)
        _ensure_files(tmp, req.files)

        # ---- ESLint (JS/TS/TSX) ----
        if _eslint_exists():
            # Use npx to avoid global eslint requirement; JSON output
            cmd = ["npx", "eslint", "-f", "json", "."]
            es = _run(cmd, tmp)
            # ESLint returns 0 (clean) or 1 (problems); >=2 means execution failure
            if es.returncode in (0, 1):
                try:
                    eslint_json = json.loads(es.stdout or "[]")
                    for file_res in eslint_json:
                        file_path = file_res.get("filePath", "")
                        for m in file_res.get("messages", []):
                            rule = (m.get("ruleId") or "-") if isinstance(m, dict) else "-"
                            sev = "error" if m.get("severity", 1) == 2 else "warning"
                            issues.append(ReviewIssue(
                                file=str(Path(file_path).as_posix()),
                                line=m.get("line"),
                                col=m.get("column"),
                                severity=sev,
                                rule=rule,
                                message=m.get("message") or "",
                                source="eslint",
                            ))
                except json.JSONDecodeError:
                    # ignore parse errors — we still have Ruff or fallback below
                    pass

        # ---- Ruff (Python) ----
        rcmd = _ruff_cmd()
        if rcmd:
            # Ruff returns non-zero when it finds issues; use JSON either way
            cmd = [*rcmd, "check", ".", "--format", "json"]
            rs = _run(cmd, tmp)
            if rs.stdout:
                try:
                    ruff_json = json.loads(rs.stdout)
                    for entry in ruff_json:
                        issues.append(ReviewIssue(
                            file=str(Path(entry.get("filename", "")).as_posix()),
                            line=(entry.get("location") or {}).get("row"),
                            col=(entry.get("location") or {}).get("column"),
                            severity="warning" if entry.get("type") == "warning" else "error",
                            rule=entry.get("code"),
                            message=entry.get("message") or "",
                            source="ruff",
                        ))
                except json.JSONDecodeError:
                    pass

        # ---- Fallback inline scan so UI isn't empty ----
        if not issues:
            for f in req.files:
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

    return LintReply(
        summary=f"Linted {len(req.files)} file(s). Found {len(issues)} issue(s).",
        issues=issues
    )
