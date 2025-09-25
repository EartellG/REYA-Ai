# backend/routes/roles_coder.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

router = APIRouter(prefix="/roles/coder", tags=["roles-coder"])

class Ticket(BaseModel):
    id: str
    title: str
    description: str
    files: List[str] = []
    acceptance: List[str] = []

class CodeGenRequest(BaseModel):
    tech_stack: Literal["react+vite+ts", "fastapi+python", "fullstack"] = "fullstack"
    ticket: Ticket
    guidance: Optional[str] = Field(default=None, description="Any extra hints for the coder")

class CodeFile(BaseModel):
    path: str
    contents: str

class CodeGenReply(BaseModel):
    summary: str
    files: List[CodeFile]

@router.post("/generate", response_model=CodeGenReply)
async def generate_code(req: CodeGenRequest):
    """
    Minimal scaffolder that returns stubbed files per ticket.
    Replace the stubs with your LLM call if desired.
    """
    files: List[CodeFile] = []
    # heuristic: decide target file types by tech_stack
    if req.tech_stack in ("react+vite+ts", "fullstack"):
        files.append(CodeFile(
            path="reya-ui/src/components/impl/Ticket_" + req.ticket.id.replace(" ", "_") + ".tsx",
            contents=f"""// Auto-generated from ticket: {req.ticket.title}
import React from "react";
/** {req.ticket.description} */
export default function Ticket_{req.ticket.id.replace('-', '_').replace(' ', '_')}() {{
  return <div>Implement: {req.ticket.title}</div>;
}}"""
        ))
    if req.tech_stack in ("fastapi+python", "fullstack"):
        files.append(CodeFile(
            path="backend/impl/ticket_" + req.ticket.id.replace("-", "_").replace(" ", "_") + ".py",
            contents=f'''# Auto-generated from ticket: {req.ticket.title}
def run():
    """{req.ticket.description}"""
    return "OK"
'''
        ))

    return CodeGenReply(
        summary=f"Generated {len(files)} file(s) for ticket {req.ticket.id}.",
        files=files,
    )
