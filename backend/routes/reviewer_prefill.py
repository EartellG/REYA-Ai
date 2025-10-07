from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/reviewer", tags=["reviewer"])

class GenFile(BaseModel):
    path: str
    contents: str

class ReviewerPrefill(BaseModel):
    ticket: dict
    files: List[GenFile]
    notes: str | None = None

_STORE: ReviewerPrefill | None = None

@router.post("/prefill")
def set_prefill(p: ReviewerPrefill):
    global _STORE
    _STORE = p
    return {"ok": True}

@router.get("/prefill")
def get_prefill():
    global _STORE
    val = _STORE
    _STORE = None  # one-shot
    return {"prefill": val}
