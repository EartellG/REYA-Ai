# backend/routes/tts_vocab.py
from fastapi import APIRouter, HTTPException
import asyncio

from backend.voice.xtts_coqui import synthesize_xtts_to_static_url

router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/vocab")
async def vocab_tts(payload: dict):
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(400, "Missing text")

    try:
        url = await asyncio.to_thread(
            synthesize_xtts_to_static_url, text, None, None
        )
        return {"audio_url": url}
    except Exception as e:
        raise HTTPException(500, f"XTTS vocab TTS failed: {e}")
