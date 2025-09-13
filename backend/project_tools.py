# backend/project_tools.py
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError
from pathlib import Path
from uuid import uuid4
from typing import Optional, List
import datetime
import json
import os
import shutil
import time
import uuid
import zipfile

# If you have this helper, great; otherwise the function is used only in /review
from backend.llm_interface import query_ollama

router = APIRouter(prefix="/proj", tags=["projects"])

# -----------------------------
# Workspace & state
# -----------------------------
WORKSPACES_DIR = Path("workspaces")
WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

UPLOADS_DIR = WORKSPACES_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ZIP_DIR = WORKSPACES_DIR / "_zips"
ZIP_DIR.mkdir(parents=True, exist_ok=True)

FIX_OUT_DIR = WORKSPACES_DIR / "fixprs"
FIX_OUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory project state for progress/logs
PROJECTS: dict[str, dict] = {}  # { project_id: {root: Path, phase: str, progress: int, log: list[dict]} }

# -----------------------------
# Prompts
# -----------------------------
ARCHITECT_PROMPT = """You are a senior software architect.
Given an APP IDEA, produce:
1) spec (<= 12 lines, concise but informative)
2) tasks: a concise checklist (<= 8 items), MVP first
3) monetization: realistic options w/ brief rationale
4) estimate: size (S/M/L) or time, with 1-line justification
5) tech_stack: recommended frameworks, DB, hosting/CDN
Return STRICT JSON with keys: spec, tasks, monetization, estimate, tech_stack, risks (optional).

APP IDEA:
{idea}

TARGET:
{target}

CONSTRAINTS:
{constraints}
"""

CODE_GEN_PROMPT = """You are a senior engineer. Generate the FULL file content.
Constraints:
- Output ONLY code (no markdown fences, no commentary).
- If the file is React/TS/JS, ensure imports are correct and paths valid.
- If backend, ensure minimal runnable scaffold.

Instruction:
{instruction}

Context (optional):
{context}
"""

REVIEW_PROMPT = """You are a strict code reviewer.
Read this repository at path: {repo_path}
Produce:
- High-level review (<= 10 bullets)
- Risk checklist (security, correctness, accessibility, performance)
- Concrete refactors with file paths
Return plain text.
"""

# -----------------------------
# Models
# -----------------------------
class Brief(BaseModel):
    idea: str
    target: str = "web"  # "web" | "mobile" | "desktop"
    constraints: List[str] = Field(default_factory=list)

class PlanResponse(BaseModel):
    spec: str = ""
    tasks: List[str] = Field(default_factory=list)
    monetization: List[str] = Field(default_factory=list)
    estimate: str = ""
    # optional but useful
    risks: List[str] = Field(default_factory=list)
    tech_stack: List[str] = Field(default_factory=list)

class ScaffoldReq(BaseModel):
    name: str
    template: str  # "react-vite", "next-app", "fastapi", "expo"
    dir: str = "workspaces"  # relative to repo root

class GenReq(BaseModel):
    path: str
    instruction: str
    context: Optional[str] = None

class GenFile(BaseModel):
    path: str
    instruction: str
    context: Optional[str] = None

class BatchFile(BaseModel):
    path: str
    content: str

class GenerateBatchReq(BaseModel):
    project_id: str
    files: List[BatchFile]
    message: Optional[str] = None

class CodeFile(BaseModel):
    path: str
    content: str

class FixPRRequest(BaseModel):
    title: str
    description: Optional[str] = None
    base_branch: str = "main"
    repo_url: Optional[str] = None
    files: List[CodeFile]

class Ticket(BaseModel):
    id: str
    title: str
    summary: str
    acceptance: List[str] = Field(default_factory=list)
    est: str = ""
    files: List[str] = Field(default_factory=list)
    area: str = ""

class TicketsResponse(BaseModel):
    tickets: List[Ticket] = Field(default_factory=list)

class GenerateFromTicketsReq(BaseModel):
    project_id: str
    tickets: List[Ticket]
    notes: Optional[str] = None

# -----------------------------
# Helpers
# -----------------------------
def _ensure_dir_is_inside(base: Path, candidate: Path) -> Path:
    base = base.resolve()
    candidate = candidate.resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path escapes workspace root")
    return candidate

def _cleanup_zip(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass

def _zip_dir(src_dir: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(src_dir):
            for f in files:
                full = Path(root) / f
                z.write(full, full.relative_to(src_dir))

def _safe_write(fp: Path, data: bytes):
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_bytes(data)

def _coerce_list(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        lines = [ln.strip("•-*0123456789. ").strip() for ln in v.splitlines()]
        return [ln for ln in lines if ln]
    return []

def _find_json_blobs(text: str) -> List[str]:
    blobs: List[str] = []
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    blobs.append(text[start:i+1])
                    start = None
    return blobs

def _best_json_from_text(text: str):
    # try full decode
    try:
        return json.loads(text)
    except Exception:
        pass
    # try each balanced {...} blob
    for blob in _find_json_blobs(text):
        try:
            return json.loads(blob)
        except Exception:
            continue
    return None

def _parse_architect_json(text: str) -> PlanResponse:
    obj = _best_json_from_text(text)
    if not obj or not isinstance(obj, dict):
        # fallback: keep something usable
        return PlanResponse(
            spec=(text.strip()[:4000] or "No spec returned."),
            tasks=[],
            monetization=[],
            estimate="Unknown",
            risks=[],
            tech_stack=[],
        )

    # coerce fields for UI stability
    data = {
        "spec": str(obj.get("spec", "")).strip(),
        "tasks": _coerce_list(obj.get("tasks", [])),
        "monetization": _coerce_list(obj.get("monetization", [])),
        "estimate": str(obj.get("estimate", "")).strip(),
        "risks": _coerce_list(obj.get("risks", [])),
        "tech_stack": _coerce_list(obj.get("tech_stack", [])),
    }
    try:
        return PlanResponse(**data)
    except ValidationError:
        return PlanResponse(
            spec=data.get("spec") or "No spec returned.",
            tasks=data.get("tasks") or [],
            monetization=data.get("monetization") or [],
            estimate=data.get("estimate") or "Unknown",
            risks=data.get("risks") or [],
            tech_stack=data.get("tech_stack") or [],
        )

def _append_log(pid: str, line: str):
    entry = {"ts": datetime.datetime.now().isoformat(), "line": line}
    PROJECTS[pid].setdefault("log", []).append(entry)

# -----------------------------
# Routes
# -----------------------------
@router.post("/plan", response_model=PlanResponse)
def plan(brief: Brief):
    """
    Project Architect: returns a structured plan as strict JSON so the UI doesn’t guess.
    """
    prompt = ARCHITECT_PROMPT.format(
        idea=brief.idea,
        target=brief.target,
        constraints="\n".join(brief.constraints) if brief.constraints else "none"
    )
    try:
        reply = query_ollama(prompt, model="mistral")
        return _parse_architect_json(reply)
    except Exception as e:
        # Safe fallback so UI still renders
        return PlanResponse(
            spec=f"⚠️ Architect error: {e}",
            tasks=[],
            monetization=[],
            estimate="Unknown",
            risks=[],
            tech_stack=[],
        )

@router.post("/tickets", response_model=TicketsResponse)
def tickets(brief: Brief):
    """
    Turns an idea into actionable tickets with file targets & acceptance criteria.
    """
    prompt = f"""
You are REYA's Ticketizer. Output ONLY JSON matching:
{{
  "tickets": [
    {{
      "id": "T-001",
      "title": "Create landing page shell",
      "summary": "Build a responsive shell with header, sidebar drawer, content area.",
      "acceptance": ["Opens on mobile", "Dark mode", "No CLS"],
      "est": "2-4h",
      "files": ["ui/src/pages/home.tsx", "ui/src/components/Shell.tsx"],
      "area": "frontend"
    }}
  ]
}}

User idea: {brief.idea!r}
Target: {brief.target}
Constraints: {brief.constraints if brief.constraints else "none"}

Rules:
- Prefer small, independently shippable tickets (MVP first).
- files = suggested paths you expect to be created/edited.
- NO prose outside JSON.
"""
    try:
        raw = query_ollama(prompt, model="mistral")
        obj = _best_json_from_text(raw) or {}
        tks = obj.get("tickets", [])
        norm: List[Ticket] = []
        for i, t in enumerate(tks):
            norm.append(Ticket(
                id=str(t.get("id") or f"T-{i+1:03}"),
                title=str(t.get("title", "")).strip(),
                summary=str(t.get("summary", "")).strip(),
                acceptance=_coerce_list(t.get("acceptance", [])),
                est=str(t.get("est", "")).strip(),
                files=[str(x).strip() for x in t.get("files", [])],
                area=str(t.get("area", "")).strip(),
            ))
        return TicketsResponse(tickets=norm)
    except Exception:
        return TicketsResponse(tickets=[])

@router.post("/generate_from_tickets")
def generate_from_tickets(req: GenerateFromTicketsReq):
    """
    For each ticket, produce a stub file (or real code later) and write into the workspace.
    """
    (WORKSPACES_DIR / req.project_id).mkdir(parents=True, exist_ok=True)

    written = 0
    for t in req.tickets:
        target = t.files[0] if t.files else f"notes/{t.id}.ts"
        guidance = "\n".join([
            f"# {t.title}",
            t.summary,
            "",
            "Acceptance:",
            *[f"- {a}" for a in t.acceptance],
            "",
            f"Area: {t.area}   Estimate: {t.est}",
            "",
            (req.notes or "")
        ])
        # NOTE: literal braces in f-strings must be doubled {{ }}
        code = (
            f"// {t.id}: {t.title}\n"
            f"/*\n{guidance}\n*/\n"
            f"export default function Stub(){{{{return null}}}}\n"
        )
        out = WORKSPACES_DIR / req.project_id / target
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(code, encoding="utf-8")
        written += 1

    # Optionally: update PROJECTS log if tracking
    pid = req.project_id
    if pid in PROJECTS:
        _append_log(pid, f"Generated {written} file(s) from tickets.")

    return {"ok": True, "generated": written}

@router.post("/upload")
async def upload(files: List[UploadFile] = File(...)):
    """
    Accepts multiple files (ZIP or regular). Saves under /workspaces/uploads/<id>/...
    Returns upload_id + file list.
    """
    up_id = uuid4().hex
    base = UPLOADS_DIR / up_id
    base.mkdir(parents=True, exist_ok=True)

    for f in files:
        data = await f.read()
        name = f.filename or "file"
        dest = base / name
        _safe_write(dest, data)
        # auto-extract a single ZIP
        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(dest, "r") as z:
                    z.extractall(base)
                dest.unlink(missing_ok=True)
            except Exception as e:
                raise HTTPException(400, f"zip extract failed: {e}")

    rel_files = [str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()]
    return {"upload_id": up_id, "saved": len(rel_files), "files": rel_files}

@router.post("/review-upload/{upload_id}")
def review_upload(upload_id: str):
    base = UPLOADS_DIR / upload_id
    if not base.exists():
        raise HTTPException(404, "upload not found")

    files = [str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()]
    report = [
        f"Upload {upload_id} contains {len(files)} files.",
        "Suggested next steps:",
        "- Run static checks (eslint/flake8).",
        "- Ask REYA to propose a refactor plan per module.",
        "- Generate unit test skeletons.",
    ]
    return {"report": "\n".join(report)}

@router.post("/scaffold")
def scaffold(req: ScaffoldReq):
    """
    Create a workspace project and register it in PROJECTS so the UI can poll /status.
    """
    # project_id: keep human-friendly; you can also append a short uuid if you prefer uniqueness
    pid = f"{req.name}".strip()
    root = WORKSPACES_DIR / pid
    root.mkdir(parents=True, exist_ok=True)

    # Minimal marker
    (root / "README.md").write_text(
        f"# {req.name}\nGenerated with template {req.template}\n",
        encoding="utf-8",
    )

    # register
    PROJECTS[pid] = {
        "root": root,
        "phase": "scaffolding",
        "progress": 10,
        "log": [{"ts": datetime.datetime.now().isoformat(), "line": f"Scaffold created for {req.template}"}],
    }

    return {"ok": True, "project_id": pid, "message": "Scaffold created", "path": str(root.resolve())}

@router.get("/status/{project_id}")
def status(project_id: str):
    info = PROJECTS.get(project_id)
    if not info:
        # Allow showing status even if user refreshes; best effort fallback from filesystem
        root = WORKSPACES_DIR / project_id
        if not root.exists():
            raise HTTPException(404, "Unknown project_id")
        return {
            "project_id": project_id,
            "phase": "unknown",
            "progress": 0,
            "log": [],
        }
    return {
        "project_id": project_id,
        "phase": info.get("phase", "unknown"),
        "progress": info.get("progress", 0),
        "log": info.get("log", []),
        "error": info.get("error"),
    }

@router.post("/generate")
def generate(req: GenReq):
    out_path = _ensure_dir_is_inside(WORKSPACES_DIR, Path(req.path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = CODE_GEN_PROMPT.format(instruction=req.instruction, context=req.context or "none")
    code = query_ollama(prompt)
    out_path.write_text(code, encoding="utf-8")
    return {"ok": True, "path": str(out_path), "bytes": len(code)}

@router.post("/generate-batch")
def generate_batch(req: GenerateBatchReq):
    pid = req.project_id
    info = PROJECTS.get(pid)

    # If not registered (e.g., server restarted), best-effort fallback
    if not info:
        root = WORKSPACES_DIR / pid
        root.mkdir(parents=True, exist_ok=True)
        info = PROJECTS[pid] = {"root": root, "phase": "generating", "progress": 5, "log": []}
    else:
        info["phase"] = "generating"

    root: Path = info["root"]

    _append_log(pid, f"Starting batch generation ({len(req.files)} files)…")
    written = 0
    for f in req.files:
        out_path = root / f.path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(f.content, encoding="utf-8")
        written += 1
        info["progress"] = min(95, info.get("progress", 5) + 3)
        _append_log(pid, f"✔ wrote {f.path}")
        time.sleep(0.05)

    # fresh zip for /download convenience
    zip_path = root / "project.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in root.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(root))

    info["phase"] = "done"
    info["progress"] = 100
    _append_log(pid, "✅ Batch generation complete. ZIP updated.")
    return {"ok": True, "written": written, "project_id": pid}

@router.get("/download")
def download_project(
    background_tasks: BackgroundTasks,
    path: Optional[str] = Query(default=None, description="Absolute or workspace-relative path returned by /proj/scaffold"),
    name: Optional[str] = Query(default=None, description="Project folder name (project_id) inside workspaces/"),
):
    if not path and not name:
        raise HTTPException(status_code=400, detail="Provide either 'path' or 'name'")

    if path:
        proj_dir = _ensure_dir_is_inside(WORKSPACES_DIR, Path(path))
    else:
        proj_dir = _ensure_dir_is_inside(WORKSPACES_DIR, WORKSPACES_DIR / name)  # type: ignore

    if not proj_dir.exists() or not proj_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Project folder not found: {proj_dir}")

    ZIP_DIR.mkdir(exist_ok=True)
    base = (ZIP_DIR / proj_dir.name).with_suffix("")  # shutil adds .zip
    zip_path_str = shutil.make_archive(base_name=str(base), format="zip", root_dir=str(proj_dir))
    zip_path = Path(zip_path_str)
    background_tasks.add_task(_cleanup_zip, zip_path)

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"{proj_dir.name}.zip",
    )

@router.post("/review")
def review(repo_path: str):
    text = REVIEW_PROMPT.format(repo_path=repo_path)
    try:
        report = query_ollama(text)
    except Exception as e:
        report = f"(review stub) Unable to call model: {e}"
    return {"report": report}

@router.post("/ship")
def ship(repo_path: str, target: str = "vercel"):
    return {
        "ok": True,
        "instructions": f"Deploy {repo_path} to {target}. Add API keys, push to GitHub, connect to {target}."
    }

@router.get("/list")
def list_projects():
    items = []
    for p in WORKSPACES_DIR.iterdir():
        if p.is_dir() and not p.name.startswith("_"):
            items.append({"name": p.name, "path": str(p.resolve())})
    return {"projects": items}

@router.post("/fix-pr")
def create_fix_pr(payload: FixPRRequest):
    if not payload.files:
        raise HTTPException(status_code=400, detail="No files provided")

    pr_id = uuid.uuid4().hex[:12]
    pr_dir = FIX_OUT_DIR / f"pr_{pr_id}"
    pr_dir.mkdir(parents=True, exist_ok=True)

    (pr_dir / "PR_INFO.txt").write_text(
        f"Title: {payload.title}\n"
        f"Base: {payload.base_branch}\n"
        f"Repo: {payload.repo_url or '(none)'}\n"
        f"Created: {datetime.datetime.now().isoformat()}\n"
        f"\n{payload.description or ''}\n",
        encoding="utf-8",
    )

    for f in payload.files:
        out_file = pr_dir / f.path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(f.content, encoding="utf-8")

    zip_path = pr_dir.with_suffix(".zip")
    _zip_dir(pr_dir, zip_path)

    return {
        "ok": True,
        "pr_id": pr_id,
        "bundle_url": f"/proj/fix-pr/{pr_id}/download",
        "message": "Simulated PR bundle created",
    }

@router.get("/fix-pr/{pr_id}/download")
def download_fix_bundle(pr_id: str):
    zip_file = (FIX_OUT_DIR / f"pr_{pr_id}").with_suffix(".zip")
    if not zip_file.exists():
        raise HTTPException(status_code=404, detail="Bundle not found")
    return FileResponse(zip_file, filename=f"fix-pr-{pr_id}.zip")
