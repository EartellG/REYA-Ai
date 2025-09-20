from fastapi import APIRouter
from pydantic import BaseModel, Field
import re
from typing import Literal

router = APIRouter(prefix="/voice", tags=["voice"])

Tab = Literal["chat", "projects", "tutor", "kb", "settings", "roles"]

class VoiceIn(BaseModel):
    text: str = Field(..., min_length=1)
    # future: device_id, user_id, lang, timestamps, etc.

class VoiceOut(BaseModel):
    intent: Tab
    confidence: float
    rationale: str

# light heuristics with soft matching; easy to swap with LLM later
def route_text(t: str) -> VoiceOut:
    s = t.strip().lower()

    # explicit wake word optional; don't require it
    s_wo_wake = re.sub(r"^\s*reya[\s,]+", "", s)

    # quick signals (projects)
    proj_patterns = [
        r"\b(app|project|idea|feature|build|scaffold|plan)\b",
        r"\b(code review|pull request|quick fix)\b",
        r"\bstart (a|the)? project\b",
    ]
    if any(re.search(p, s_wo_wake) for p in proj_patterns):
        return VoiceOut(intent="projects", confidence=0.8, rationale="project keywords")

    # tutor signals (language)
    tutor_patterns = [
        r"\b(japanese|mandarin|chinese|language tutor|let'?s learn)\b",
        r"\bpractice (speaking|pronunciation|kana|kanji|tones?)\b",
        r"\bquiz me\b",
    ]
    if any(re.search(p, s_wo_wake) for p in tutor_patterns):
        return VoiceOut(intent="tutor", confidence=0.8, rationale="tutor keywords")

    # roles (ticketizer etc.)
    if re.search(r"\b(ticket|tickets?|acceptance criteria)\b", s_wo_wake):
        return VoiceOut(intent="roles", confidence=0.7, rationale="role/ticket signals")

    # settings/KB lightweight
    if re.search(r"\bsettings?\b", s_wo_wake):
        return VoiceOut(intent="settings", confidence=0.6, rationale="settings mention")
    if re.search(r"\bknowledge\s*base|kb\b", s_wo_wake):
        return VoiceOut(intent="kb", confidence=0.6, rationale="KB mention")

    # fallback: chat
    return VoiceOut(intent="chat", confidence=0.4, rationale="fallback")

@router.post("/route", response_model=VoiceOut)
def route(inb: VoiceIn):
    return route_text(inb.text)
