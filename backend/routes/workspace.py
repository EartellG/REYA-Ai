# backend/routes/workspace.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime
import os  # <-- import before using os.getenv
from difflib import unified_diff 

router = APIRouter(prefix="/workspace", tags=["workspace"])

# ----- Config: where files are allowed to be saved -----
# Default = repo root (two levels up from this file: backend/routes/.. -> repo)
_DEFAULT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = Path(
    os.getenv("REYA_WORKSPACE_ROOT", str(_DEFAULT_ROOT))
).resolve()

# ----- Models -----
class FileBlob(BaseModel):
    path: str = Field(..., min_length=1)      # relative path (e.g., "reya-ui/src/App.tsx")
    contents: str = Field(..., min_length=0)

class SaveRequest(BaseModel):
    files: List[FileBlob]
    backup: bool = True                       # create timestamped .bak before overwrite
    overwrite: bool = True                    # allow overwriting existing files

class SaveResult(BaseModel):
    path: str
    saved: bool
    message: Optional[str] = None
    backup_path: Optional[str] = None

class SaveReply(BaseModel):
    ok: bool
    root: str
    results: List[SaveResult]
    stats: Dict[str, int]

# ----- Helpers -----
def _guarded_path(rel: str) -> Path:
    """
    Resolve a user-provided relative path under WORKSPACE_ROOT.
    Prevents absolute paths and .. traversal.
    """
    p = Path(rel)
    if p.is_absolute():
        # detail must be passed as a keyword argument
        raise HTTPException(status_code=400, detail=f"Absolute paths are not allowed: {rel}")

    full = (WORKSPACE_ROOT / p).resolve()

    # Ensure full is inside WORKSPACE_ROOT (or equals it)
    if WORKSPACE_ROOT not in full.parents and full != WORKSPACE_ROOT:
        raise HTTPException(status_code=400, detail=f"Path escapes workspace root: {rel}")

    return full

def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")

# ----- Routes -----
@router.get("/root")
def get_root():
    return {"root": str(WORKSPACE_ROOT)}

@router.post("/save", response_model=SaveReply)
def save_files(req: SaveRequest):
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    results: List[SaveResult] = []
    saved = skipped = errors = 0

    for f in req.files:
        try:
            target = _guarded_path(f.path)

            # ensure parent dirs
            target.parent.mkdir(parents=True, exist_ok=True)

            # backup if requested and file exists
            bak_path = None
            if req.backup and target.exists():
                bak_path = target.with_suffix(target.suffix + f".{_timestamp()}.bak")
                bak_path.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")

            # if file exists and overwrite is false -> skip
            if target.exists() and not req.overwrite:
                results.append(SaveResult(
                    path=f.path, saved=False, message="File exists; overwrite disabled.",
                    backup_path=(str(bak_path) if bak_path else None),
                ))
                skipped += 1
                continue

            # write file
            target.write_text(f.contents, encoding="utf-8")
            results.append(SaveResult(
                path=f.path, saved=True, backup_path=(str(bak_path) if bak_path else None)
            ))
            saved += 1

        except HTTPException:
            # re-raise guarded path errors
            raise
        except Exception as e:
            results.append(SaveResult(path=f.path, saved=False, message=str(e)))
            errors += 1

    return SaveReply(
        ok=(errors == 0),
        root=str(WORKSPACE_ROOT),
        results=results,
        stats={"saved": saved, "skipped": skipped, "errors": errors, "total": len(req.files)},
    )

class DiffRequest(BaseModel):
    files: List[FileBlob]

class FileDiff(BaseModel):
    path: str
    diff: str  # unified diff text

class DiffReply(BaseModel):
    diffs: List[FileDiff]

@router.post("/diff", response_model=DiffReply)
def diff_files(req: DiffRequest):
    """
    Compares provided file contents against current on-disk versions
    under WORKSPACE_ROOT. Returns unified diffs for preview.
    """
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    diffs: List[FileDiff] = []

    for f in req.files:
        target = _guarded_path(f.path)
        current = ""
        try:
            if target.exists():
                current = target.read_text(encoding="utf-8")
        except Exception as ex:
            raise HTTPException(status_code=500, detail=f"Failed to read {f.path}: {ex}")

        diff_text = "".join(
            unified_diff(
                current.splitlines(keepends=True),
                f.contents.splitlines(keepends=True),
                fromfile=f"a/{f.path}",
                tofile=f"b/{f.path}",
                lineterm=""
            )
        )
        diffs.append(FileDiff(path=f.path, diff=diff_text))

    return DiffReply(diffs=diffs)
