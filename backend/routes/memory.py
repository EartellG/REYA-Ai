# backend/routes/memory.py
# FIX: use a *relative* import so it always finds the shared core inside the backend package.
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..main import core  # <-- relative import (NOT "from main import core")

router = APIRouter(prefix="/memory", tags=["memory"])

class PrimaryUserIn(BaseModel):
  name: str
  alias: Optional[str] = None
  is_admin: bool = True

@router.get("/primary_user")
def get_primary_user():
  return core.identity.status()

@router.post("/primary_user")
def set_primary_user(payload: PrimaryUserIn):
  ident = core.identity.set_primary_user(payload.name, payload.alias, payload.is_admin)
  return {"ok": True, "primary_user": ident}
