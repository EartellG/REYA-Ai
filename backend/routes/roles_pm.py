from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
import hashlib

router = APIRouter(prefix="/roles/pm", tags=["roles-pm"])

TicketType = Literal["Backend", "Frontend", "QA"]

class SpecInput(BaseModel):
    title: str = Field(..., description="Short name for the feature/epic")
    goal: str = Field(..., description="What outcome do we want?")
    background: Optional[str] = Field(None, description="Context, current behavior, links")
    constraints: Optional[str] = Field(None, description="Must/should nots, tech limits")
    non_goals: Optional[str] = Field(None, description="Explicitly out of scope")
    include_qa: bool = True
    estimate_units: Literal["pts", "hrs"] = "pts"

class UserStory(BaseModel):
    role: str
    need: str
    why: str

class Ticket(BaseModel):
    id: str
    title: str
    type: TicketType
    estimate: float
    acceptance_criteria: List[str]
    tags: List[str] = []

class TicketizeResponse(BaseModel):
    epic: str
    user_stories: List[UserStory]
    tickets: List[Ticket]


# --- simple deterministic heuristics (no LLM) ---

def _mk_id(seed: str) -> str:
    return hashlib.sha1(seed.encode()).hexdigest()[:8]


def _estimate_for(section: str, units: str = "pts") -> float:
    base = {
        "backend": 3.0,
        "frontend": 3.0,
        "qa": 2.0,
    }[section]
    return base if units == "pts" else base * 2.5  # naive hours mapping


def _acceptance_gwt(title: str, details: str) -> List[str]:
    return [
        f"Given the app is running,",
        f"When I complete: {title} — {details[:90]}…",
        f"Then I see the expected behavior without errors and with persisted state as applicable.",
    ]


@router.post("/ticketize", response_model=TicketizeResponse)
async def ticketize(spec: SpecInput) -> TicketizeResponse:
    # Epic
    epic = f"{spec.title}: {spec.goal.strip()}"

    # Stories
    stories = [
        UserStory(role="end user", need=spec.goal.strip(), why="to achieve the stated outcome"),
        UserStory(role="developer", need="clear toggles and server API", why="to implement confidently"),
    ]

    # Tickets (Backend, Frontend, QA)
    tickets: List[Ticket] = []

    # Backend ticket
    be_title = f"Backend: {spec.title} API + schema"
    tickets.append(
        Ticket(
            id=_mk_id(be_title),
            title=be_title,
            type="Backend",
            estimate=_estimate_for("backend", spec.estimate_units),
            acceptance_criteria=_acceptance_gwt(be_title, spec.background or spec.goal),
            tags=["roles", "pm", "api"],
        )
    )

    # Frontend ticket
    fe_title = f"Frontend: {spec.title} UI + state"
    tickets.append(
        Ticket(
            id=_mk_id(fe_title),
            title=fe_title,
            type="Frontend",
            estimate=_estimate_for("frontend", spec.estimate_units),
            acceptance_criteria=_acceptance_gwt(fe_title, spec.constraints or spec.goal),
            tags=["roles", "pm", "ui"],
        )
    )

    # QA ticket
    if spec.include_qa:
        qa_title = f"QA: {spec.title} e2e + acceptance"
        tickets.append(
            Ticket(
                id=_mk_id(qa_title),
                title=qa_title,
                type="QA",
                estimate=_estimate_for("qa", spec.estimate_units),
                acceptance_criteria=[
                    "Checklist covers happy path, error states, and reload/persistence.",
                    "Playwright e2e asserts visible UI changes and no console errors.",
                ],
                tags=["roles", "pm", "qa"],
            )
        )

    return TicketizeResponse(epic=epic, user_stories=stories, tickets=tickets)