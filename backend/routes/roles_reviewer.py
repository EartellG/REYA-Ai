# backend/routes/roles_reviewer.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import re

router = APIRouter(prefix="/roles/reviewer", tags=["roles:reviewer"])

# -------- one-shot prefill buffer (Coder -> Reviewer handoff) --------
_PREFILL: Optional[dict] = None

# --------- Models (legacy + new unified) ---------
class Ticket(BaseModel):
    id: str
    title: str
    type: Optional[Literal["Backend", "Frontend", "QA"]] = None
    estimate: Optional[float] = None
    tags: Optional[List[str]] = None
    acceptance_criteria: Optional[List[str]] = None
    summary: Optional[str] = None
    context: Optional[str] = None
    description: Optional[str] = None

class FilePatch(BaseModel):
    path: str = Field(..., min_length=1)
    contents: str = Field(..., min_length=1)

class ReviewRequest(BaseModel):
    # New fields (optional, for richer flows)
    ticket: Optional[Ticket] = None
    files: List[FilePatch]
    notes: Optional[str] = None
    # simple filter like "severity:error" or "path:src/components"
    filter: Optional[str] = None

# New detailed issue
class ReviewIssue(BaseModel):
    id: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    col: Optional[int] = None
    severity: Literal["error", "warning", "info"]
    message: str
    suggestion: Optional[str] = None
    rule: Optional[str] = None

# Legacy finding shape (kept for UI compatibility)
class ReviewFinding(BaseModel):
    path: str
    notes: List[str]

# Unified reply (contains both)
class ReviewReply(BaseModel):
    ok: bool = True
    summary: str
    issues: List[ReviewIssue] = []
    findings: List[ReviewFinding] = []

# ---------------- Prefill endpoints ----------------
@router.get("/prefill")
def get_prefill():
    """Coder -> Reviewer handoff (one-shot)."""
    global _PREFILL
    if not _PREFILL:
        return {"prefill": None}
    buf = _PREFILL
    _PREFILL = None  # consume
    return {"prefill": buf}

@router.post("/prefill")
def set_prefill(payload: dict):
    """Optional: allow UI/tests to push a prefill directly."""
    global _PREFILL
    _PREFILL = payload
    return {"ok": True}

# ---------------- Simple static checks ----------------
def _simple_checks(path: str, contents: str) -> List[ReviewIssue]:
    issues: List[ReviewIssue] = []

    # Rule: disallow console.log
    for ln, line in enumerate(contents.splitlines(), start=1):
        if "console.log(" in line:
            issues.append(ReviewIssue(
                file=path, line=ln, severity="warning",
                message="Avoid console.log in committed code.",
                suggestion="Use a logger utility or remove debug output.",
                rule="no-console",
            ))

    # Rule: TODO / FIXME
    for ln, line in enumerate(contents.splitlines(), start=1):
        if re.search(r"\b(TODO|FIXME)\b", line, re.IGNORECASE):
            issues.append(ReviewIssue(
                file=path, line=ln, severity="info",
                message="Found TODO/FIXME comment.",
                suggestion="Create a ticket or resolve before merge.",
                rule="tracking-comment",
            ))

    # Rule: alert()
    for ln, line in enumerate(contents.splitlines(), start=1):
        if re.search(r"\balert\s*\(", line):
            issues.append(ReviewIssue(
                file=path, line=ln, severity="warning",
                message="Avoid blocking alert() in production UI.",
                suggestion="Use a non-blocking toast/snackbar component.",
                rule="no-alert",
            ))

    # Rule: any (very rough TS smell)
    for ln, line in enumerate(contents.splitlines(), start=1):
        if re.search(r"\bany\b", line) and not re.search(r"//\s*eslint-disable", contents):
            issues.append(ReviewIssue(
                file=path, line=ln, severity="info",
                message="TypeScript 'any' detected.",
                suggestion="Tighten types where feasible.",
                rule="ts-no-explicit-any",
            ))

    # Rule: long lines > 120
    for ln, line in enumerate(contents.splitlines(), start=1):
        if len(line) > 120:
            issues.append(ReviewIssue(
                file=path, line=ln, severity="info",
                message=f"Line exceeds 120 characters ({len(line)}).",
                suggestion="Wrap string or refactor for readability.",
                rule="max-len",
            ))

    # Rule: duplicate imports
    import_re = re.compile(r"^\s*import\s+.*\s+from\s+['\"](.+)['\"]\s*;?\s*$")
    seen: dict[str, int] = {}
    for ln, line in enumerate(contents.splitlines(), start=1):
        m = import_re.match(line)
        if m:
            mod = m.group(1)
            seen[mod] = seen.get(mod, 0) + 1
            if seen[mod] > 1:
                issues.append(ReviewIssue(
                    file=path, line=ln, severity="info",
                    message=f"Duplicate import of '{mod}'.",
                    suggestion="Merge import statements.",
                    rule="no-duplicate-imports",
                ))

    return issues

# --------------- Main review endpoint ---------------
@router.post("/review", response_model=ReviewReply)
async def review(req: ReviewRequest):
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    all_issues: List[ReviewIssue] = []
    for f in req.files:
        # soft guard on huge files
        if len(f.contents) > 500_000:
            all_issues.append(ReviewIssue(
                file=f.path, severity="warning",
                message=f"File too large for quick review ({len(f.contents)} bytes).",
                suggestion="Run full reviewer pipeline locally.",
                rule="size-limit",
            ))
            continue
        all_issues.extend(_simple_checks(f.path, f.contents))

    # Optional result filtering
    if req.filter:
        flt = req.filter.strip().lower()
        def _keep(i: ReviewIssue) -> bool:
            if flt.startswith("severity:"):
                return i.severity == flt.split(":", 1)[1]
            if flt.startswith("path:"):
                return (i.file or "").lower().startswith(flt.split(":", 1)[1])
            return True
        all_issues = [i for i in all_issues if _keep(i)]

    # Build legacy findings (group by file with note strings)
    findings_map: dict[str, List[str]] = {}
    for i in all_issues:
        msg = i.message
        if i.suggestion:
            msg += f" — Suggestion: {i.suggestion}"
        key = i.file or "<unknown>"
        findings_map.setdefault(key, []).append(msg)
    findings = [ReviewFinding(path=k, notes=v) for k, v in findings_map.items()]

    summary = f"Reviewed {len(req.files)} file(s). Found {len(all_issues)} issue(s)."
    return ReviewReply(ok=True, summary=summary, issues=all_issues, findings=findings)

# ---------- Back-compat aliases ----------
@router.post("/checks", response_model=ReviewReply)
async def checks(req: ReviewRequest):
    return await review(req)

@router.post("/run", response_model=ReviewReply)
async def run(req: ReviewRequest):
    return await review(req)
