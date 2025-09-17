# backend/routes/settings.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json
import threading

router = APIRouter(prefix="/settings", tags=["settings"])

# Where to persist settings (alongside backend/)
SETTINGS_PATH = (Path(__file__).parent.parent / "settings.json").resolve()
_LOCK = threading.Lock()

class SettingsPayload(BaseModel):
    multimodal: bool = False
    liveAvatar: bool = False
    logicEngine: bool = False
    offlineSmart: bool = False

def _read_settings() -> SettingsPayload:
    if not SETTINGS_PATH.exists():
        return SettingsPayload()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return SettingsPayload(**data)
    except Exception:
        # reset on corruption
        return SettingsPayload()

def _write_settings(sp: SettingsPayload) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(sp.model_dump_json(indent=2), encoding="utf-8")

@router.get("", response_model=SettingsPayload)
def get_settings():
    with _LOCK:
        return _read_settings()

@router.post("", response_model=SettingsPayload)
def post_settings(payload: SettingsPayload):
    try:
        with _LOCK:
            _write_settings(payload)
            return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}")
