# backend/routes/tickets.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/tickets", tags=["tickets"])

# ---- In-memory handoff cache for the Coder panel ----
# Frontend Coder panel will read this to prefill its form.
_CODER_PREFILL: Dict[str, Any] = {}

class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    context: Optional[str] = None           # extra notes, acceptance criteria, etc.
    source_discussion_id: Optional[str] = None

class SendToCoderRequest(BaseModel):
    ticket: Ticket
    # optional guidance for the coder panel
    language: Optional[str] = None          # e.g., "TypeScript", "Python"
    framework: Optional[str] = None         # e.g., "React", "FastAPI"
    target_dir: Optional[str] = None        # where to place files in repo (hint)

class SendToCoderResponse(BaseModel):
    ok: bool
    message: str
    coder_prefill: Dict[str, Any]

@router.post("/send_to_coder", response_model=SendToCoderResponse)
async def send_to_coder(payload: SendToCoderRequest):
    """
    Stores a single 'prefill' package for the Coder panel to consume.
    Frontend can GET /tickets/coder_prefill to retrieve and fill its form.
    """
    if not payload.ticket or not payload.ticket.title or not payload.ticket.summary:
        raise HTTPException(status_code=422, detail="Ticket requires at least title and summary.")

    # Build the package the Coder panel expects to prefill its inputs.
    package = {
        "ticket_id": payload.ticket.id,
        "title": payload.ticket.title.strip(),
        "goal": payload.ticket.summary.strip(),
        "tags": payload.ticket.tags or [],
        "context": (payload.ticket.context or "").strip(),
        "hints": {
            "language": payload.language,
            "framework": payload.framework,
            "target_dir": payload.target_dir,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source_discussion_id": payload.ticket.source_discussion_id,
    }

    # Save to a simple in-memory slot (latest handoff wins).
    _CODER_PREFILL.clear()
    _CODER_PREFILL.update(package)

    return SendToCoderResponse(
        ok=True,
        message="Ticket sent to Coder prefill.",
        coder_prefill=package,
    )

@router.get("/coder_prefill")
async def get_coder_prefill():
    """
    The Coder panel hits this to load the most recent prefill.
    Returns {} if nothing is queued.
    """
    return _CODER_PREFILL or {}

@router.post("/clear_prefill")
async def clear_coder_prefill():
    _CODER_PREFILL.clear()
    return {"ok": True}
