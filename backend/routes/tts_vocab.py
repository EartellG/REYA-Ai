# backend/routes/tts_vocab.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import time, hashlib, traceback

from backend.voice.edge_tts import default_voice_for_text, synthesize_to_file

router = APIRouter(prefix="/tts", tags=["tts"])
STATIC_DIR = Path("static/audio")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

class TTSReq(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str | None = None  # e.g. "ja-JP-NanamiNeural", "zh-CN-XiaoxiaoNeural"

@router.post("", summary="Synthesize text and return a URL")
async def synthesize(req: TTSReq):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text required")

    voice = req.voice or default_voice_for_text(text)
    key = hashlib.sha1(f"{voice}|{text}|{int(time.time())}".encode()).hexdigest()[:12]
    out_path = STATIC_DIR / f"tts_{key}.mp3"

    try:
        await synthesize_to_file(text, reya=None, out_path=str(out_path), voice_override=voice)
        return {"url": f"/static/audio/{out_path.name}", "voice": voice}
    except Exception as e:
        # return the exact error so we can see what's wrong in dev
        tb = traceback.format_exc(limit=2)
        raise HTTPException(status_code=500, detail=f"TTS failed: {e} | {tb}")
