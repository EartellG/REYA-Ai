from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from typing import Optional
from backend.voice.edge_tts import synthesize_to_static_url, default_voice_for_text, synth_to_bytes

router = APIRouter(prefix="/tts", tags=["tts"])

class TTSReq(BaseModel):
    text: str = Field(..., min_length=1)
    voice: Optional[str] = None

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

@router.get("/vocab_bytes", summary="Edge-only bytes test")
async def synthesize_vocab_bytes(text: str = Query(...), voice: Optional[str] = Query(None)):
    voice = voice or default_voice_for_text(text)
    audio, meta = await synth_to_bytes(text, voice=voice)
    media = meta.get("format", "audio/mpeg")
    return Response(content=audio, media_type=media, headers={
        "X-REYA-TTS-Engine": meta.get("engine",""),
        "X-REYA-TTS-Voice": meta.get("voice",""),
    })
