from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from typing import Optional

from backend.voice.speech_manager import synthesize_tts

from pathlib import Path
import os
import uuid

router = APIRouter(tags=["tts"])

@router.post("/tts")
async def tts_endpoint(payload: dict):
    """
    XTTS-only TTS endpoint.
    Returns: { audio_url: "/static/audio/xxx.wav" }
    """
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing text")

    try:
        # generate static audio file
        audio_dir = Path("backend/static/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)

        filename = f"reya_{uuid.uuid4().hex}.wav"
        filepath = audio_dir / filename

        output_path = synthesize_tts(text, filename=str(filepath))

        url = "/static/audio/" + filename
        return {"audio_url": url}

    except Exception as e:
        return JSONResponse(
            {"detail": f"TTS failed: {str(e)}"},
            status_code=500
        )
