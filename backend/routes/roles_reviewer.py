# backend/routes/roles_reviewer.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/roles/reviewer", tags=["roles-reviewer"])

class FilePatch(BaseModel):
    path: str
    contents: str

class ReviewRequest(BaseModel):
    files: List[FilePatch]

class ReviewFinding(BaseModel):
    path: str
    notes: List[str]

class ReviewReply(BaseModel):
    summary: str
    findings: List[ReviewFinding]

@router.post("/review", response_model=ReviewReply)
async def review(req: ReviewRequest):
    # simple placeholder checks (expand with real lint/results or LLM)
    findings: List[ReviewFinding] = []
    for f in req.files:
        notes = []
        if "console.log" in f.contents:
            notes.append("Avoid console.log in committed code.")
        if "any" in f.contents:
            notes.append("TypeScript: reduce 'any' usage if possible.")
        if "TODO" in f.contents:
            notes.append("Resolve TODOs before merging.")
        if notes:
            findings.append(ReviewFinding(path=f.path, notes=notes))
    return ReviewReply(
        summary=f"Reviewed {len(req.files)} file(s). {len(findings)} with notes.",
        findings=findings
    )
