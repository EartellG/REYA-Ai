# backend/git_tools.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import os
import git  # GitPython

from .config import REYA_REPOS_ROOT

router = APIRouter(prefix="/git", tags=["git"])

class LocalCommitReq(BaseModel):
    repo_path: str                # absolute or relative to REYA_REPOS_ROOT
    branch: str | None = None     # default new feature branch
    title: str
    description: str = ""
    files: list[dict]             # [{path: "src/x.ts", content: "..."}]
    push: bool = False            # only if remotes configured

def _resolve_repo_path(repo_path: str) -> Path:
    p = Path(repo_path)
    if not p.is_absolute():
        p = (REYA_REPOS_ROOT / p).resolve()
    # security: must live under allowlisted root
    try:
        p.relative_to(REYA_REPOS_ROOT)
    except ValueError:
        raise HTTPException(status_code=400, detail="Repo path not under allowed root")
    return p

@router.post("/commit-local")
def commit_local(req: LocalCommitReq):
    repo_dir = _resolve_repo_path(req.repo_path)
    if not repo_dir.exists():
        raise HTTPException(status_code=404, detail="Repo not found")

    try:
        repo = git.Repo(str(repo_dir))
    except Exception:
        raise HTTPException(status_code=400, detail="Not a git repository")

    # create feature branch (or checkout existing)
    branch = req.branch or f"reya/fix-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    try:
        if branch in repo.heads:
            repo.git.checkout(branch)
        else:
            repo.git.checkout("-b", branch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout failed: {e}")

    # write files
    for f in req.files:
        rel = Path(f["path"]).as_posix().lstrip("/")
        abs_path = repo_dir / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(f["content"], encoding="utf-8")

    # stage + commit
    try:
        repo.git.add("-A")
        msg = req.title.strip()
        if req.description.strip():
            msg = f"{msg}\n\n{req.description.strip()}"
        # if nothing to commit, Git will error—handle gracefully
        if not repo.is_dirty(index=True, working_tree=True, untracked_files=True):
            return {"ok": True, "branch": branch, "commit": None, "note": "No changes to commit"}
        repo.index.commit(msg)
        commit_sha = repo.head.commit.hexsha[:10]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Commit failed: {e}")

    pushed = False
    if req.push:
        try:
            # choose 'origin' if exists
            remote = repo.remotes.origin if "origin" in [r.name for r in repo.remotes] else repo.remotes[0]
            remote.push(branch)
            pushed = True
        except Exception as e:
            # don’t fail the request for a push error, just report it
            return {"ok": True, "branch": branch, "commit": commit_sha, "pushed": False, "push_error": str(e)}

    return {"ok": True, "branch": branch, "commit": commit_sha, "pushed": pushed}
