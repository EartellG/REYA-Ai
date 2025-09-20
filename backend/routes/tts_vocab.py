from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from backend.voice.edge_tts import synthesize_to_static_url, default_voice_for_text

router = APIRouter(prefix="/tts", tags=["tts"])  # yields /tts/vocab

class TTSReq(BaseModel):
    text: str = Field(..., min_length=1)
    voice: Optional[str] = None  # e.g. "ja-JP-NanamiNeural"

@router.post("/vocab", summary="Synthesize text for vocab and return a URL")
async def synthesize_vocab(req: TTSReq):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text required")
    voice = req.voice or default_voice_for_text(text)
    try:
        url = await synthesize_to_static_url(text, reya=None, voice_override=voice)
        return {"url": url, "voice": voice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")
