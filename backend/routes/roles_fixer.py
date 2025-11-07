# backend/routes/roles_fixer.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Tuple
from pathlib import Path
import difflib
import re
import os

router = APIRouter(prefix="/roles/fixer", tags=["roles-fixer"])

# -------- One-shot prefill buffer (Reviewer -> Fixer handoff) --------
_PREFILL: Optional[dict] = None

@router.get("/prefill")
def get_prefill():
    """
    One-shot prefill fetch for FixerPanel. Returns {"prefill": None} if empty.
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
    Allow Reviewer to stage files/issues for Fixer.
    """
    global _PREFILL
    _PREFILL = payload or {}
    return {"ok": True}


# ---------------- Models ----------------
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
    source: Optional[str] = None  # "eslint" | "ruff" | "inline"

class Finding(BaseModel):  # legacy shape from static review
    path: str
    notes: List[str]

class SuggestReq(BaseModel):
    files: List[FileBlob]
    issues: Optional[List[ReviewIssue]] = None
    findings: Optional[List[Finding]] = None
    strategy: Optional[Literal["safe", "aggressive"]] = "safe"
    only_paths: Optional[List[str]] = None

class Patch(BaseModel):
    path: str
    diff: str  # unified diff (display only)

class SuggestResp(BaseModel):
    ok: bool
    summary: str
    patches: List[Patch]
    stats: Optional[Dict[str, int]] = None

class ApplyReq(BaseModel):
    files: List[FileBlob]
    patches: List[Patch]

class ApplyResp(BaseModel):
    ok: bool
    summary: str
    files: List[FileBlob]

class ApplyAndSaveReq(BaseModel):
    files: List[FileBlob]
    patches: List[Patch]

class ApplyAndSaveResp(BaseModel):
    ok: bool
    summary: str
    written: int
    files_written: List[str]
    errors: List[str]
    files: List[FileBlob]


# ---------------- Utility transforms ----------------
def _transform_js_ts(code: str, strategy: str = "safe") -> str:
    """
    Simple fixer rules for JS/TS:
    - remove console.log lines
    - strip TODO/FIXME comments
    - (aggressive) replace any with unknown in TypeScript
    """
    out_lines: List[str] = []
    for line in code.splitlines():
        # remove console.log (common lint rule)
        if re.search(r"\bconsole\.log\s*\(", line):
            continue
        # strip single-line TODO/FIXME comments
        if re.search(r"//\s*(TODO|FIXME)\b", line):
            continue
        out_lines.append(line)

    fixed = "\n".join(out_lines)

    if strategy == "aggressive":
        # replace standalone : any with : unknown (basic TS hygiene)
        fixed = re.sub(r":\s*any\b", ": unknown", fixed)

    return fixed

def _transform_python(code: str, strategy: str = "safe") -> str:
    """
    Simple fixer rules for Python:
    - remove TODO / FIXME comments
    - (aggressive) strip unused import lines heuristically (very naive)
    """
    out_lines: List[str] = []
    for line in code.splitlines():
        if re.search(r"#\s*(TODO|FIXME)\b", line):
            continue
        out_lines.append(line)
    fixed = "\n".join(out_lines)

    if strategy == "aggressive":
        # naive removal of obvious unused imports like: "import pdb" or "from pdb import set_trace"
        fixed = re.sub(r"^\s*(from\s+\w+\s+import\s+\w+|import\s+\w+)\s*$", "", fixed, flags=re.MULTILINE)

    return fixed

def _suggest_for_file(path: str, contents: str, strategy: str) -> Tuple[str, Optional[str]]:
    """
    Returns (new_contents, unified_diff or None if no change)
    """
    ext = Path(path).suffix.lower()
    if ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        new_contents = _transform_js_ts(contents, strategy)
    elif ext == ".py":
        new_contents = _transform_python(contents, strategy)
    else:
        # no transform
        new_contents = contents

    if new_contents == contents:
        return contents, None

    diff = difflib.unified_diff(
        contents.splitlines(keepends=True),
        new_contents.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm=""
    )
    return new_contents, "".join(diff)


# ---------------- Suggest patches ----------------
@router.post("/suggest_patches", response_model=SuggestResp)
def suggest_patches(req: SuggestReq):
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    only = set(req.only_paths or [])
    patches: List[Patch] = []
    changed = 0
    inspected = 0

    # If issues/findings provided, prioritize those paths
    candidate_paths = set(f.path for f in req.files)
    if req.issues:
        for it in req.issues:
            if it.file:
                candidate_paths.add(it.file)
    if req.findings:
        for f in req.findings:
            if f.path:
                candidate_paths.add(f.path)

    for fb in req.files:
        if only and fb.path not in only:
            continue
        if fb.path not in candidate_paths:
            continue
        inspected += 1
        new_contents, udiff = _suggest_for_file(fb.path, fb.contents, req.strategy or "safe")
        if udiff:
            patches.append(Patch(path=fb.path, diff=udiff))
            changed += 1

    summary = f"Analyzed {inspected} file(s). Produced {len(patches)} patch(es)."
    return SuggestResp(ok=True, summary=summary, patches=patches, stats={"inspected": inspected, "changed": changed})


# ---------------- Apply patches (in-memory) ----------------
@router.post("/apply", response_model=ApplyResp)
def apply(req: ApplyReq):
    """
    Applies fixes by re-running the same deterministic transforms used in suggest_patches.
    We do NOT parse unified diff; the diff is for display only.
    """
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    by_path = {f.path: f for f in req.files}
    out_files: List[FileBlob] = []
    touched = 0

    for f in req.files:
        new_contents, udiff = _suggest_for_file(f.path, f.contents, "safe")
        if udiff:
            out_files.append(FileBlob(path=f.path, contents=new_contents))
            touched += 1
        else:
            out_files.append(f)

    return ApplyResp(ok=True, summary=f"Applied fixes to {touched} file(s) in memory.", files=out_files)


# ---------------- Apply & Save to workspace ----------------
WORKSPACE_ROOT = Path(os.environ.get("REYA_WORKSPACE_ROOT", ".")).resolve()

@router.post("/apply_and_save", response_model=ApplyAndSaveResp)
def apply_and_save(req: ApplyAndSaveReq):
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    by_path = {f.path: f for f in req.files}
    out_files: List[FileBlob] = []
    files_written: List[str] = []
    errors: List[str] = []
    touched = 0

    for f in req.files:
        new_contents, udiff = _suggest_for_file(f.path, f.contents, "safe")
        out = FileBlob(path=f.path, contents=new_contents if udiff else f.contents)
        out_files.append(out)

        # write to workspace
        try:
            abs_path = (WORKSPACE_ROOT / f.path).resolve()
            if WORKSPACE_ROOT not in abs_path.parents and WORKSPACE_ROOT != abs_path:
                errors.append(f"Refused to write outside workspace: {abs_path}")
                continue
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as fp:
                fp.write(out.contents)
            files_written.append(str(abs_path))
            if udiff:
                touched += 1
        except Exception as ex:
            errors.append(f"{f.path}: {ex}")

    summary = f"Applied fixes to {touched} file(s). Wrote {len(files_written)} file(s) to workspace."
    return ApplyAndSaveResp(
        ok=len(errors) == 0,
        summary=summary,
        written=len(files_written),
        files_written=files_written,
        errors=errors,
        files=out_files
    )
