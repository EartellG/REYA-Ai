# backend/routes/roles_reviewer.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Literal

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

# ---------------- (optional) Lint stubs ----------------
class LintFile(BaseModel):
    path: str
    contents: str

class LintPayload(BaseModel):
    files: List[LintFile]

class ReviewIssue(BaseModel):
    id: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    col: Optional[int] = None
    severity: Literal["error", "warning", "info"] = "info"
    message: str
    suggestion: Optional[str] = None
    rule: Optional[str] = None
    source: Optional[str] = None  # "eslint" | "ruff"

class LintReply(BaseModel):
    summary: str
    issues: List[ReviewIssue]

@router.get("/lint/health")
def lint_health():
    # Just enough for the UI indicator
    import shutil, sys
    return {
        "ok": True,
        "tools": {
            "npx": bool(shutil.which("npx")),
            "eslint": bool(shutil.which("eslint")),
            "ruff": bool(shutil.which("ruff") or shutil.which("ruff.exe")),
            "python": sys.executable,
        },
    }

@router.post("/lint", response_model=LintReply)
async def lint_files(payload: LintPayload):
    # Placeholder—your actual ESLint/Ruff integration can replace this.
    issues: List[ReviewIssue] = []
    for f in payload.files:
        if "console.log" in f.contents:
            issues.append(ReviewIssue(
                file=f.path, severity="warning", message="Unexpected console.log", rule="no-console", source="eslint"
            ))
    return LintReply(summary=f"Linted {len(payload.files)} file(s).", issues=issues)
