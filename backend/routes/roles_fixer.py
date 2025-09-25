# backend/routes/roles_fixer.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/roles/fixer", tags=["roles-fixer"])

class Finding(BaseModel):
    path: str
    notes: List[str]

class FixRequest(BaseModel):
    files: List[str]          # file paths to consider
    findings: List[Finding]   # from reviewer

class Patch(BaseModel):
    path: str
    diff: str                 # unified diff (placeholder)

class FixReply(BaseModel):
    summary: str
    patches: List[Patch]

@router.post("/suggest_patches", response_model=FixReply)
async def suggest_patches(req: FixRequest):
    patches: List[Patch] = []
    for f in req.findings:
        # naive example: emit a stub diff per finding
        patches.append(Patch(
            path=f.path,
            diff=f"""--- a/{f.path}
+++ b/{f.path}
@@
- // TODO: fix issue
+ // FIXED: addressed reviewer notes
"""
        ))
    return FixReply(summary=f"Suggested {len(patches)} patch(es).", patches=patches)
