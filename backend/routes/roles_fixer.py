# backend/routes/roles_fixer.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from pathlib import Path
import re
import difflib
import datetime
import os



router = APIRouter(prefix="/roles/fixer", tags=["roles:fixer"])

# ---------- one-shot prefill buffer (Reviewer -> Fixer handoff) ----------
_PREFILL: Optional[dict] = None

# ---------- Models ----------
class FileBlob(BaseModel):
    path: str = Field(..., min_length=1)
    contents: str = Field(..., min_length=0)

# Legacy finding (Reviewer v1)
class Finding(BaseModel):
    path: str
    notes: List[str]

# Rich issue (Reviewer v2)
class ReviewIssue(BaseModel):
    id: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    col: Optional[int] = None
    severity: Literal["error", "warning", "info"] = "info"
    message: str
    suggestion: Optional[str] = None
    rule: Optional[str] = None

class FixRequest(BaseModel):
    files: List[FileBlob]
    findings: Optional[List[Finding]] = None   # legacy
    issues: Optional[List[ReviewIssue]] = None # new
    strategy: Optional[Literal["safe", "aggressive"]] = "safe"
    only_paths: Optional[List[str]] = None

class Patch(BaseModel):
    path: str
    diff: str  # unified diff

class FixReply(BaseModel):
    ok: bool = True
    summary: str
    patches: List[Patch]
    stats: Dict[str, int] = {}

class ApplyRequest(BaseModel):
    files: List[FileBlob]
    patches: List[Patch]

class ApplyReply(BaseModel):
    ok: bool
    summary: str
    files: List[FileBlob]

class ApplyAndSaveReply(BaseModel):
    ok: bool
    summary: str
    written: int
    files_written: list[str] = []
    errors: list[str] = []
    files: list[FileBlob] = []  # echo of updated files (for UI preview if needed)

# ---------- Prefill endpoints (Reviewer -> Fixer handoff) ----------
@router.get("/prefill")
def get_prefill():
    """Retrieve one-shot handoff payload (clears after read)."""
    global _PREFILL
    if not _PREFILL:
        return {"prefill": None}
    buf = _PREFILL
    _PREFILL = None
    return {"prefill": buf}

@router.post("/prefill")
def set_prefill(payload: dict):
    """Store a one-shot handoff blob from Reviewer (files, findings, ticket)."""
    global _PREFILL
    _PREFILL = payload
    return {"ok": True, "stored": True}

# ---------- Helpers ----------
_CONSOLE_RE = re.compile(r"\bconsole\.log\s*\(")
_ALERT_RE   = re.compile(r"\balert\s*\(")
_TODO_RE    = re.compile(r"\b(TODO|FIXME)\b", re.IGNORECASE)
_ANY_RE     = re.compile(r"(?<!\w)any(?!\w)")
_DUP_SPACES = re.compile(r"[ \t]+$")  # trailing spaces


def _write_files(files: list[FileBlob]) -> tuple[int, list[str], list[str]]:
    """
    Writes FileBlob list to disk.
    Returns: (written_count, written_paths, errors)
    """
    written = 0
    paths: list[str] = []
    errors: list[str] = []

    for f in files:
        try:
            p = Path(f.path)
            # prevent directory traversal into system roots if you want (optional guard)
            # if not str(p.resolve()).startswith(str(Path(".").resolve())):
            #     errors.append(f"Blocked write outside workspace: {f.path}")
            #     continue

            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f.contents, encoding="utf-8")
            written += 1
            paths.append(f.path)
        except Exception as e:
            errors.append(f"{f.path}: {e!r}")
    return written, paths, errors

def _apply_simple_auto_fixes(src: str, path: str, strategy: str) -> str:
    """
    Conservative auto-fixes:
      - remove or comment out console.log / alert lines
      - trim trailing spaces
      - annotate or rewrite TODO/FIXME
      - replace 'any' with 'unknown' in TS when aggressive
    """
    out_lines: List[str] = []
    is_ts_like = path.endswith((".ts", ".tsx"))

    for line in src.splitlines(keepends=False):
        # Trim trailing spaces
        line = _DUP_SPACES.sub("", line)

        # console.log
        if _CONSOLE_RE.search(line):
            if strategy == "aggressive":
                continue
            else:
                line = f"// removed by fixer: {line}"

        # alert()
        if _ALERT_RE.search(line):
            if strategy == "aggressive":
                continue
            else:
                line = f"// replaced alert() by fixer; use toast/snackbar\n// {line}"

        # TODO/FIXME
        if _TODO_RE.search(line):
            if strategy == "aggressive":
                line = f"// TODO handled by fixer: " + line
            else:
                line = line + "  // NOTE: tracked by Fixer"

        # TypeScript 'any'
        if is_ts_like and _ANY_RE.search(line):
            if strategy == "aggressive":
                line = _ANY_RE.sub("unknown", line)

        out_lines.append(line)

    return "\n".join(out_lines) + ("\n" if src.endswith("\n") else "")

def _unified_diff(path: str, before: str, after: str) -> str:
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        fromfiledate=ts,
        tofiledate=ts,
        n=3,
    )
    return "".join(diff)

# ---------- Core: suggest patches ----------
@router.post("/suggest_patches", response_model=FixReply)
async def suggest_patches(req: FixRequest):
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    file_map: Dict[str, str] = {f.path: f.contents for f in req.files}
    target_paths = set(req.only_paths or file_map.keys())

    if req.issues:
        target_paths &= {i.file for i in req.issues if i.file}
    elif req.findings:
        target_paths &= {f.path for f in req.findings}

    patches: List[Patch] = []
    edited = 0
    unchanged = 0

    for path in sorted(target_paths):
        before = file_map.get(path)
        if before is None:
            continue

        after = _apply_simple_auto_fixes(before, path, req.strategy or "safe")

        if after != before:
            diff = _unified_diff(path, before, after)
            if diff.strip():
                patches.append(Patch(path=path, diff=diff))
                edited += 1
        else:
            unchanged += 1

    summary = f"Analyzed {len(target_paths)} file(s): {edited} patched, {unchanged} unchanged."
    stats = {"files_seen": len(target_paths), "patched": edited, "unchanged": unchanged}
    return FixReply(ok=True, summary=summary, patches=patches, stats=stats)

# ---------- Apply patches ----------
@router.post("/apply", response_model=ApplyReply)
async def apply_patches(req: ApplyRequest):
    """
    Applies patches in-memory (re-runs our safe fix rules per file).
    Returns updated file contents.
    """
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")
    if not req.patches:
        return ApplyReply(ok=True, summary="No patches provided.", files=req.files)

    contents_by_path = {f.path: f.contents for f in req.files}
    touched = 0

    for p in req.patches:
        if p.path in contents_by_path:
            before = contents_by_path[p.path]
            after = _apply_simple_auto_fixes(before, p.path, "safe")
            if after != before:
                contents_by_path[p.path] = after
                touched += 1

    updated_files = [FileBlob(path=k, contents=v) for k, v in contents_by_path.items()]
    return ApplyReply(ok=True, summary=f"Applied {touched} patch(es) in memory.", files=updated_files)

@router.post("/apply_and_save", response_model=ApplyAndSaveReply)
async def apply_and_save(req: ApplyRequest):
    """
    Applies patches in-memory (same as /apply) then writes results to disk.
    """
    # reuse /apply behavior to get updated in-memory files
    applied = await apply_patches(req)
    if not applied.ok:
        return ApplyAndSaveReply(ok=False, summary=applied.summary, written=0, files=applied.files)

    written, paths, errs = _write_files(applied.files)
    ok = written > 0 and len(errs) == 0
    summary = f"Wrote {written} file(s)." + (f" {len(errs)} error(s)." if errs else "")
    return ApplyAndSaveReply(
        ok=ok,
        summary=summary,
        written=written,
        files_written=paths,
        errors=errs,
        files=applied.files,
    )
