# backend/routes/roles_monetizer.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/roles/monetizer", tags=["roles-monetizer"])

class Feature(BaseModel):
    name: str
    value: str

class MonetizeRequest(BaseModel):
    app_idea: str
    audience: str
    features: List[Feature] = []

class MonetizePlan(BaseModel):
    pricing: List[str]
    tiers: List[str]
    notes: List[str]

@router.post("/plan", response_model=MonetizePlan)
async def plan(req: MonetizeRequest):
    pricing = [
        "Free: limited usage, watermark, community support",
        "Pro: $9–$19/mo, full usage, no watermark, priority support",
        "Team: $49–$99/mo, seats, roles, analytics",
    ]
    tiers = [
        "Starter → Pro → Team",
        "One-time add-ons: export packs, premium voices, extra storage",
    ]
    notes = [
        f"Target audience: {req.audience}",
        "Highlight differentiation: fast iteration from idea → ticket → code → review.",
        "Bundle with templates for common app types (chat, tutor, dashboard).",
    ]
    return MonetizePlan(pricing=pricing, tiers=tiers, notes=notes)
