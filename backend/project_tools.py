# backend/project_tools.py
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi import UploadFile, File
from uuid import uuid4
import datetime
import shutil
from backend.llm_interface import query_ollama
from typing import List, Optional
import time
import zipfile
import uuid
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from fastapi.responses import FileResponse
import datetime, os, shutil, zipfile
from typing import Optional, List



router = APIRouter(prefix="/proj", tags=["projects"])
PROJECTS = {}



# Root folder for all projects
WORKSPACES_DIR = Path("workspaces")
WORKSPACES_DIR.mkdir(exist_ok=True)

# Uploads_DIR 
UPLOADS_DIR = WORKSPACES_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Subfolder to temporarily store generated zips
ZIP_DIR = WORKSPACES_DIR / "_zips"
ZIP_DIR.mkdir(exist_ok=True)

###---PROMPTS----###
ARCHITECT_PROMPT = """You are a senior software architect.
Given an APP IDEA, produce:
1) short spec (<= 12 lines)
2) tasks: a concise checklist (<= 8 items)
3) files: a proposed file tree with purpose notes
4) env: recommended tech stack (frameworks, libs)
Return strict JSON with keys: spec, tasks, files, env.
APP IDEA:
"""

CODE_GEN_PROMPT = """You are a senior engineer. Generate the FULL file content.
Constraints:
- Output ONLY code (no markdown fences, no commentary).
- If the file is React or TS/JS, ensure imports are correct and relative paths valid.
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

# --- Models ---
class Brief(BaseModel):
    idea: str
    target: str = "web"  # web | mobile | desktop
    constraints: list[str] = []


class ScaffoldReq(BaseModel):
    name: str
    template: str  # "react-vite", "next-app", "fastapi", "expo"
    dir: str = "workspaces"  # where to place the scaffold


class GenReq(BaseModel):
    path: str
    instruction: str
    context: str | None = None
    

class GenFile(BaseModel):
    path: str
    instruction: str
    context: str | None = None

class GenBatchReq(BaseModel):
    files: list[GenFile]

class BatchFile(BaseModel):
    path: str
    content: str

class GenerateBatchReq(BaseModel):
    project_id: str
    files: List[BatchFile]          # payload of files to write
    message: Optional[str] = None   # optional “why / summary”

class CodeFile(BaseModel):
    path: str          # e.g. "src/app.tsx"
    content: str       # full file text

class FixPRRequest(BaseModel):
    title: str
    description: Optional[str] = None
    base_branch: str = "main"
    repo_url: Optional[str] = None   # optional for future GitHub integration
    files: List[CodeFile]


# --- Helpers ---
def _ensure_dir_is_inside(base: Path, candidate: Path) -> Path:
    """
    Prevents directory traversal outside WORKSPACES_DIR.
    Returns resolved candidate if it's inside base; otherwise raises HTTPException.
    """
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

def _gen_one_file(g: GenFile) -> dict:
    out_path = _ensure_dir_is_inside(WORKSPACES_DIR, Path(g.path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = CODE_GEN_PROMPT.format(instruction=g.instruction, context=g.context or "none")
    code = query_ollama(prompt)
    out_path.write_text(code, encoding="utf-8")
    return {"ok": True, "path": str(out_path), "bytes": len(code)}

def _safe_write(fp: Path, data: bytes):
  fp.parent.mkdir(parents=True, exist_ok=True)
  fp.write_bytes(data)

FIX_OUT_DIR = WORKSPACES_DIR / "fixprs"
FIX_OUT_DIR.mkdir(parents=True, exist_ok=True)

def _zip_dir(src_dir: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(src_dir):
            for f in files:
                full = Path(root) / f
                z.write(full, full.relative_to(src_dir))



# --- Routes ---
@router.post("/plan")
def plan(brief: Brief):
    prompt = ARCHITECT_PROMPT + f"{brief.idea}\nTarget: {brief.target}\nConstraints: {brief.constraints}"
    raw = query_ollama(prompt)  # uses your default mistral
    # Try to coerce to JSON safely
    import json
    try:
        data = json.loads(raw)
    except Exception:
        # naive recovery: find first/last braces
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start:end+1]) if start != -1 and end != -1 else {
            "spec": f"Spec for {brief.idea} targeting {brief.target}.",
            "tasks": ["Scaffold project", "Build core", "Auth", "Tests", "Deploy"],
            "files": ["README.md - project overview"],
            "env": ["vite", "react", "fastapi"]
        }
    return data


@router.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    """
    Accepts multiple files (ZIP or regular). Saves under /workspaces/uploads/<id>/...
    Returns upload_id + file list.
    """
    up_id = str(uuid4())
    base = UPLOADS_DIR / up_id
    base.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for f in files:
        data = await f.read()
        name = f.filename or "file"
        dest = base / name
        _safe_write(dest, data)
        saved.append(name)

        # Auto-extract single zip
        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(dest, "r") as z:
                    z.extractall(base)
                dest.unlink(missing_ok=True)
            except Exception as e:
                return {"error": f"zip extract failed: {e}"}

    # Return a flat listing (relative)
    rel_files = []
    for p in base.rglob("*"):
        if p.is_file():
            rel_files.append(str(p.relative_to(base)))

    return {"upload_id": up_id, "saved": len(rel_files), "files": rel_files}

@router.post("/review-upload/{upload_id}")
def review_upload(upload_id: str):
    """
    Very lightweight review that leverages your existing LLM review flow later.
    For now, just builds a quick report of contents.
    """
    base = UPLOADS_DIR / upload_id
    if not base.exists():
        raise HTTPException(404, "upload not found")

    files = [str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()]
    # TODO: feed file samples into your LLM code-review prompt
    report = [
        f"Upload {upload_id} contains {len(files)} files.",
        "Suggested next steps:",
        "- Run static checks (eslint/flake8).",
        "- Ask REYA to propose a refactor plan per module.",
        "- Generate unit tests skeletons.",
    ]
    # You can call your existing review(repo_path) here if you want:
    # return review(str(base))  # if you adapt it to accept a path to analyze

    return {"report": "\n".join(report)}


@router.post("/scaffold")
def scaffold(req: ScaffoldReq):
    root = Path(req.dir) / req.name
    root.mkdir(parents=True, exist_ok=True)

    # Minimal scaffold marker
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(f"# {req.name}\nGenerated with template {req.template}\n")

    # Return a normalized workspace path so the UI can feed it to /proj/download
    return {"ok": True, "path": str(root.resolve())}


@router.post("/generate")
def generate(req: GenReq):
    out_path = Path(req.path)
    # Keep file writes inside the workspace for safety
    out_path = _ensure_dir_is_inside(WORKSPACES_DIR, out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    content = (
        f"// Placeholder code for: {req.instruction}\n"
        f"// Context: {req.context or 'none'}\n"
    )
    out_path.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(out_path), "lines": content.count('\n') + 1}


@router.post("/generate-batch")
def generate_batch(req: GenerateBatchReq):
    pid = req.project_id
    if pid not in PROJECTS:
        raise HTTPException(404, "Unknown project_id")

    info = PROJECTS[pid]
    root = info["root"]

    # mark phase
    info["phase"] = "generating"
    _append_log(pid, f"Starting batch generation ({len(req.files)} files)…")

    written = 0
    for f in req.files:
        out_path = root / f.path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(f.content, encoding="utf-8")
        written += 1
        info["progress"] = min(95, info["progress"] + 3)
        _append_log(pid, f"✔ wrote {f.path}")
        time.sleep(0.05)  # tiny delay so UI shows streaming logs

    # zip fresh
    zip_path = root / "project.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in root.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(root))

    info["phase"] = "done"
    info["progress"] = 100
    _append_log(pid, f"✅ Batch generation complete. ZIP updated.")



    return {"ok": True, "written": written, "project_id": pid}

def _append_log(pid, message):
    # Log storage could be a dictionary, a list, or even a database
    log_storage = PROJECTS[pid].get("log", [])
    log_storage.append(message)
    PROJECTS[pid]["log"] = log_storage


@router.post("/review")
def review(repo_path: str):
    # (Future: walk the tree & include key files—be careful with size)
    text = REVIEW_PROMPT.format(repo_path=repo_path)
    report = query_ollama(text)
    return {"report": report}



@router.post("/ship")
def ship(repo_path: str, target: str = "vercel"):
    # Stub: Later generate CI/CD configs
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



@router.get("/download")
def download_project(
    background_tasks: BackgroundTasks,
    path: str | None = Query(
        default=None,
        description="Absolute or workspace-relative path returned by /proj/scaffold",
    ),
    name: str | None = Query(
        default=None,
        description="Project folder name inside the workspaces/ directory",
    ),
):
    """
    Create a ZIP of a project directory and return it.
    Provide EITHER `path` (preferred, from /proj/scaffold) OR `name` (found under workspaces/).
    """
    if not path and not name:
        raise HTTPException(status_code=400, detail="Provide either 'path' or 'name'")

    if path:
        proj_dir = Path(path)
        # keep downloads inside workspace
        proj_dir = _ensure_dir_is_inside(WORKSPACES_DIR, proj_dir)
    else:
        proj_dir = _ensure_dir_is_inside(WORKSPACES_DIR, WORKSPACES_DIR / name) # type: ignore

    if not proj_dir.exists() or not proj_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Project folder not found: {proj_dir}")
    

    # Create zip in ZIP_DIR, then stream it and delete afterward
    ZIP_DIR.mkdir(exist_ok=True)
    base = (ZIP_DIR / proj_dir.name).with_suffix("")  # shutil adds .zip
    zip_path_str = shutil.make_archive(base_name=str(base), format="zip", root_dir=str(proj_dir))
    zip_path = Path(zip_path_str)

    # Clean up the temp zip after the response finishes
    background_tasks.add_task(_cleanup_zip, zip_path)

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"{proj_dir.name}.zip",
    )

@router.post("/fix-pr")
def create_fix_pr(payload: FixPRRequest):
    """
    Simulates a PR by writing patched files into a branch-like folder
    and returning a downloadable zip. Later you can swap this to a real
    GitHub PR if GITHUB_TOKEN is configured.
    """
    if not payload.files:
        raise HTTPException(status_code=400, detail="No files provided")

    pr_id = uuid.uuid4().hex[:12]
    pr_dir = FIX_OUT_DIR / f"pr_{pr_id}"
    pr_dir.mkdir(parents=True, exist_ok=True)

    # store metadata
    (pr_dir / "PR_INFO.txt").write_text(
        f"Title: {payload.title}\n"
        f"Base: {payload.base_branch}\n"
        f"Repo: {payload.repo_url or '(none)'}\n"
        f"Created: {datetime.datetime.now().isoformat()}\n"
        f"\n{payload.description or ''}\n"
    )

    # write files
    for f in payload.files:
        out_file = pr_dir / f.path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(f.content, encoding="utf-8")

    # zip it
    zip_path = pr_dir.with_suffix(".zip")
    _zip_dir(pr_dir, zip_path)

    return {
        "ok": True,
        "pr_id": pr_id,
        "bundle_url": f"/proj/fix-pr/{pr_id}/download",  # GET below
        "message": "Simulated PR bundle created",
    }

@router.get("/fix-pr/{pr_id}/download")
def download_fix_bundle(pr_id: str):
    zip_file = (FIX_OUT_DIR / f"pr_{pr_id}").with_suffix(".zip")
    if not zip_file.exists():
        raise HTTPException(status_code=404, detail="Bundle not found")
    return FileResponse(zip_file, filename=f"fix-pr-{pr_id}.zip")

