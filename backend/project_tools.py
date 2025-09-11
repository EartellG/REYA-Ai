# backend/project_tools.py
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from fastapi.responses import FileResponse
import datetime
import shutil
from backend.llm_interface import query_ollama
router = APIRouter(prefix="/proj", tags=["projects"])

# Root folder for all projects
WORKSPACES_DIR = Path("workspaces")
WORKSPACES_DIR.mkdir(exist_ok=True)

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
def generate_batch(req: GenBatchReq):
    results = [_gen_one_file(g) for g in req.files]
    return {"ok": True, "results": results}


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
        proj_dir = _ensure_dir_is_inside(WORKSPACES_DIR, WORKSPACES_DIR / name)

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
