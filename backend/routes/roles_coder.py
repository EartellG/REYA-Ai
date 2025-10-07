# backend/routes/roles_coder.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Tuple
from pathlib import Path

router = APIRouter(prefix="/roles/coder", tags=["roles:coder"])

# ---------- one-shot prefill buffer (Ticketizer -> Coder handoff) ----------
_PREFILL: Optional[dict] = None

# ---------- Models ----------
class Ticket(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    files: List[str] = []
    acceptance: List[str] = []
    tags: List[str] = []

class CodeGenRequest(BaseModel):
    tech_stack: Literal["react+vite+ts", "fastapi+python", "fullstack"] = "fullstack"
    ticket: Ticket
    guidance: Optional[str] = Field(default=None, description="Extra hints for the coder")

class CodeFile(BaseModel):
    path: str
    contents: str

class CodeGenReply(BaseModel):
    ok: bool = True
    summary: str
    files: List[CodeFile]

class SaveRequest(BaseModel):
    files: List[CodeFile]
    overwrite: bool = False

class SaveReply(BaseModel):
    ok: bool
    written: int
    skipped: int
    errors: List[str]
    files_written: List[str] = []
    summary: str = ""

class GenAndSaveRequest(CodeGenRequest):
    overwrite: bool = False

class GenAndSaveReply(BaseModel):
    ok: bool
    summary: str
    generated: int
    written: int
    skipped: int
    errors: List[str]
    files_written: List[str] = []

# ---------- Project roots (restrict writes to these) ----------
# This file lives at: backend/routes/roles_coder.py
# parents[0] = routes, [1] = backend, [2] = <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_ROOTS = [
    PROJECT_ROOT / "reya-ui",
    PROJECT_ROOT / "backend",
]

def _normalize_and_validate(rel_or_project_path: str) -> Tuple[Path, Path]:
    """
    Return (abs_path, root) if the path is inside an allowed root; else raise.
    - Reject absolute paths.
    - Reject paths that resolve outside the allowed roots (path traversal).
    """
    if not rel_or_project_path:
        raise HTTPException(status_code=422, detail="Empty file path")

    p = Path(rel_or_project_path)

    if p.is_absolute():
        # For safety, disallow absolute; require repo-relative paths
        raise HTTPException(status_code=422, detail=f"Absolute paths not allowed: {rel_or_project_path}")

    # Treat given path as project-root relative by default
    abs_path = (PROJECT_ROOT / p).resolve()

    # Must fall under one of the allowed roots
    for root in ALLOWED_ROOTS:
        try:
            abs_path.relative_to(root.resolve())
            return abs_path, root
        except ValueError:
            continue

    raise HTTPException(
        status_code=422,
        detail=f"Path is outside allowed roots: {rel_or_project_path}",
    )

# ---------- Prefill endpoints (Ticketizer -> Coder handoff) ----------
@router.get("/prefill")
async def get_prefill():
    """Retrieve one-shot handoff payload (clears after read)."""
    global _PREFILL
    if not _PREFILL:
        return {"prefill": None}
    buf = _PREFILL
    _PREFILL = None
    return {"prefill": buf}

@router.post("/prefill")
async def set_prefill(payload: dict):
    """Store a one-shot handoff blob from Ticketizer (ticket spec, notes)."""
    global _PREFILL
    _PREFILL = payload
    return {"ok": True, "stored": True}

# ---------- Code generation ----------
@router.post("/generate", response_model=CodeGenReply)
async def generate_code(req: CodeGenRequest):
    """
    Minimal scaffolder that returns stubbed files per ticket.
    Replace the stubs with your LLM or template generator later.
    """
    files: List[CodeFile] = []

    if req.tech_stack in ("react+vite+ts", "fullstack"):
        comp_name = req.ticket.id.replace("-", "_").replace(" ", "_")
        files.append(CodeFile(
            path=f"reya-ui/src/components/impl/Ticket_{comp_name}.tsx",
            contents=f"""// Auto-generated from ticket: {req.ticket.title}
// Description: {req.ticket.description or "N/A"}
import React from "react";

export default function Ticket_{comp_name}() {{
  return (
    <div className="p-4">
      <h3>{req.ticket.title}</h3>
      <p>{req.ticket.description}</p>
    </div>
  );
}}"""
        ))

    if req.tech_stack in ("fastapi+python", "fullstack"):
        mod_name = req.ticket.id.replace("-", "_").replace(" ", "_").lower()
        files.append(CodeFile(
            path=f"backend/impl/ticket_{mod_name}.py",
            contents=f'''"""
Auto-generated backend stub for ticket: {req.ticket.title}
Description: {req.ticket.description or "N/A"}
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/ticket/{req.ticket.id.lower()}")
def run():
    """Implements {req.ticket.title}"""
    return {{"status": "ok", "ticket": "{req.ticket.id}"}}
'''
        ))

    return CodeGenReply(
        ok=True,
        summary=f"Generated {len(files)} file(s) for ticket {req.ticket.id}.",
        files=files,
    )

# ---------- Save to workspace ----------
@router.post("/save", response_model=SaveReply)
async def save_files(req: SaveRequest):
    """
    Write files to disk under allowed roots (backend/, reya-ui/).
    - Rejects absolute/out-of-root paths.
    - Creates parent folders as needed.
    - Skips existing files unless overwrite=True.
    """
    if not req.files:
        raise HTTPException(status_code=422, detail="No files to save")

    written = 0
    skipped = 0
    errors: List[str] = []
    files_written: List[str] = []

    for f in req.files:
        try:
            abs_path, _root = _normalize_and_validate(f.path)
            if abs_path.exists() and not req.overwrite:
                skipped += 1
                continue

            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(f.contents, encoding="utf-8")
            written += 1
            files_written.append(str(abs_path.relative_to(PROJECT_ROOT)))
        except HTTPException as he:
            errors.append(he.detail)
        except Exception as e:
            errors.append(f"{f.path}: {e!r}")

    summary = f"Saved {written} file(s), skipped {skipped}, {len(errors)} error(s)."
    return SaveReply(
        ok=(written > 0 and len(errors) == 0),
        written=written,
        skipped=skipped,
        errors=errors,
        files_written=files_written,
        summary=summary,
    )

# ---------- Generate and save in one call ----------
@router.post("/generate_and_save", response_model=GenAndSaveReply)
async def generate_and_save(req: GenAndSaveRequest):
    """
    Convenience endpoint:
      1) Generate stubs for the ticket.
      2) Save them to disk (respecting overwrite flag).
    """
    gen = await generate_code(CodeGenRequest(tech_stack=req.tech_stack, ticket=req.ticket, guidance=req.guidance))
    save = await save_files(SaveRequest(files=gen.files, overwrite=req.overwrite))

    summary = f"{gen.summary} {save.summary}"
    ok = save.ok and gen.ok

    return GenAndSaveReply(
        ok=ok,
        summary=summary,
        generated=len(gen.files),
        written=save.written,
        skipped=save.skipped,
        errors=save.errors,
        files_written=save.files_written,
    )
