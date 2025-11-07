# backend/features/identity.py
from __future__ import annotations
from typing import Optional, Dict

class IdentityStore:
    """
    Thin facade that uses a ContextualMemory-like dict to persist identity.
    You can back this with your existing ContextualMemory instance.
    """
    def __init__(self, memory):
        self.memory = memory   # expects ContextualMemory-like object (has .history and .save())

    def _bucket(self) -> Dict:
        return self.memory.history.setdefault("identity", {})

    # ---------- Primary user ----------
    def set_primary_user(self, name: str, alias: Optional[str] = None, is_admin: bool = True):
        b = self._bucket()
        b["primary_user"] = {"name": name.strip(), "alias": (alias or "").strip() or None, "is_admin": bool(is_admin)}
        self.memory.save()
        return b["primary_user"]

    def get_primary_user(self) -> Optional[Dict]:
        return self._bucket().get("primary_user")

    # ---------- Helpers ----------
    def preferred_display_name(self) -> Optional[str]:
        pu = self.get_primary_user()
        if not pu: 
            return None
        return pu.get("alias") or pu.get("name")

    def status(self) -> Dict:
        pu = self.get_primary_user()
        return {
            "primary_user": pu or None,
            "has_primary_user": bool(pu),
        }
