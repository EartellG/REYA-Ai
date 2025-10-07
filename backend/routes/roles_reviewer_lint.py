# backend/routes/roles_reviewer_lint.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import tempfile, subprocess, json, os, sys, shutil
from pathlib import Path

router = APIRouter(prefix="/roles/reviewer", tags=["roles:reviewer:lint"])
UI_DIR = (Path(__file__).resolve().parents[2] / "reya-ui").resolve()

# ---------- Models ----------
class FileBlob(BaseModel):
    path: str = Field(..., min_length=1)
    contents: str = Field(..., min_length=0)

class ReviewIssue(BaseModel):
    id: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    col: Optional[int] = None
    severity: Literal["error", "warning", "info"] = "info"
    message: str
    suggestion: Optional[str] = None
    rule: Optional[str] = None
    source: Optional[str] = None   # "eslint" | "ruff"

class LintRequest(BaseModel):
    files: List[FileBlob]
    # Optional: limit which tools to run
    tools: Optional[List[Literal["eslint", "ruff"]]] = None

class LintReply(BaseModel):
    ok: bool
    summary: str
    issues: List[ReviewIssue]
    tools: Dict[str, Any] = {}

def _write_temp_tree(files: List[FileBlob]) -> str:
    td = tempfile.mkdtemp(prefix="reya_lint_")
    for f in files:
        # ensure directories exist inside temp
        full = os.path.join(td, f.path.replace("\\", "/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(f.contents)
    return td

def _have_cmd(cmd: List[str]) -> bool:
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return True
    except Exception:
        return False
    
def _run(cmd: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    try:
        out = subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT)
        return True, out.decode("utf-8", "ignore").strip()
    except Exception as e:
        msg = ""
        if hasattr(e, "output") and e.output: # pyright: ignore[reportAttributeAccessIssue]
            try:
                msg = e.output.decode("utf-8", "ignore") # pyright: ignore[reportAttributeAccessIssue]
            except Exception:
                msg = str(e)
        return False, msg or str(e)

def _run_eslint(root: str) -> Dict[str, Any]:
    """
    Run ESLint with JSON formatter over TS/TSX/JS/JSX in the temp tree.
    We try 'npx eslint' first; if that fails, try plain 'eslint' in PATH.
    """
    base_cmd = None
    if shutil.which("npx"):
        base_cmd = ["npx", "eslint", "-f", "json", "--ext", ".ts,.tsx,.js,.jsx", "."]
    elif shutil.which("eslint"):
        base_cmd = ["eslint", "-f", "json", "--ext", ".ts,.tsx,.js,.jsx", "."]
    else:
        return {"ok": False, "error": "eslint not found (install with npm -D eslint)", "issues": []}

    try:
        proc = subprocess.run(
            base_cmd,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
        )
        # ESLint returns non-zero when it finds problems — still parseable.
        out = proc.stdout.strip() or "[]"
        data = json.loads(out)
        issues: List[ReviewIssue] = []
        for file_entry in data:
            filename = file_entry.get("filePath", "")
            for m in file_entry.get("messages", []):
                sev_num = m.get("severity", 1)
                sev = "error" if sev_num == 2 else "warning"
                msg = m.get("message", "")
                rule = m.get("ruleId")
                issues.append(ReviewIssue(
                    id=str(m.get("ruleId") or "ESLINT"),
                    file=os.path.relpath(filename, root).replace("\\", "/"),
                    line=m.get("line"),
                    col=m.get("column"),
                    severity=sev, message=msg, rule=rule,
                    suggestion=(m.get("fix") and "Auto-fix available") or None,
                    source="eslint",
                ))
        return {"ok": True, "issues": [i.dict() for i in issues], "stderr": proc.stderr}
    except Exception as e:
        return {"ok": False, "error": f"eslint run failed: {e}", "issues": []}

def _run_ruff(root: str) -> Dict[str, Any]:
    """
    Run Ruff with JSON output over Python files.
    """
    ruff_path = shutil.which("ruff") or shutil.which(os.path.join(os.path.dirname(sys.executable), "ruff"))
    if not ruff_path:
        # Try 'python -m ruff'
        py_cmd = [sys.executable, "-m", "ruff", "version"]
        if not _have_cmd(py_cmd):
            return {"ok": False, "error": "ruff not found (pip install ruff)", "issues": []}
        base_cmd = [sys.executable, "-m", "ruff", "check", "--output-format", "json", "."]
    else:
        base_cmd = [ruff_path, "check", "--output-format", "json", "."]

    try:
        proc = subprocess.run(
            base_cmd,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
        )
        out = proc.stdout.strip() or "[]"
        data = json.loads(out)
        issues: List[ReviewIssue] = []
        for item in data:
            filename = item.get("filename", "")
            loc = item.get("location", {}) or {}
            code = item.get("code")
            msg = item.get("message", "")
            issues.append(ReviewIssue(
                id=str(code or "RUFF"),
                file=os.path.relpath(filename, root).replace("\\", "/"),
                line=loc.get("row"),
                col=loc.get("column"),
                severity="warning" if str(code).startswith(("E", "F")) else "info",
                message=msg,
                rule=str(code) if code else None,
                source="ruff",
            ))
        return {"ok": True, "issues": [i.dict() for i in issues], "stderr": proc.stderr}
    except Exception as e:
        return {"ok": False, "error": f"ruff run failed: {e}", "issues": []}

@router.get("/lint/health")
def lint_health():
    npx_ok = shutil.which("npx") is not None

    # Try local eslint from the UI dir
    eslint_ok = False
    if npx_ok:
        ok, _ = _run(["npx", "eslint", "-v"], cwd=UI_DIR)
        eslint_ok = ok
        if not eslint_ok:
            # fallback: call the local binary directly via node
            candidate = UI_DIR / "node_modules" / ".bin" / ("eslint.cmd" if sys.platform.startswith("win") else "eslint")
            if candidate.exists():
                ok, _ = _run([str(candidate), "-v"], cwd=UI_DIR)
                eslint_ok = ok

    # Ruff: prefer module form so PATH doesn’t matter
    ruff_ok, _ = _run([sys.executable, "-m", "ruff", "--version"])

    return {
        "ok": True,
        "tools": {
            "npx": npx_ok,
            "eslint": bool(eslint_ok),
            "ruff": bool(ruff_ok),
            "python": sys.executable,
            "ui_dir": str(UI_DIR),
        },
    }
@router.post("/lint", response_model=LintReply)
async def lint_files(req: LintRequest):
    if not req.files:
        raise HTTPException(status_code=422, detail="No files provided")

    root = _write_temp_tree(req.files)
    try:
        wanted = set(req.tools or ["eslint", "ruff"])
        issues: List[ReviewIssue] = []
        tool_status: Dict[str, Any] = {}

        if "eslint" in wanted:
            eslint_result = _run_eslint(root)
            tool_status["eslint"] = {k: v for k, v in eslint_result.items() if k != "issues"}
            if eslint_result.get("ok"):
                for it in eslint_result["issues"]:
                    issues.append(ReviewIssue(**it))
        if "ruff" in wanted:
            ruff_result = _run_ruff(root)
            tool_status["ruff"] = {k: v for k, v in ruff_result.items() if k != "issues"}
            if ruff_result.get("ok"):
                for it in ruff_result["issues"]:
                    issues.append(ReviewIssue(**it))

        issues_sorted = sorted(
            issues,
            key=lambda i: (i.file or "", (i.line or 0), 0 if i.severity == "error" else 1),
        )
        return LintReply(
            ok=True,
            summary=f"Found {len(issues_sorted)} issue(s) across {len(req.files)} file(s).",
            issues=issues_sorted,
            tools=tool_status,
        )
    finally:
        try:
            shutil.rmtree(root, ignore_errors=True)
        except Exception:
            pass
