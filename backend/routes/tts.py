# backend/routes/tts.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from backend.voice.edge_tts import synthesize_to_static_url  # <-- canonical helper

router = APIRouter(tags=["tts"])

def _first_nonempty(*vals):
    for v in vals:
        if v is not None and str(v).strip():
            return str(v)
    return None

@router.api_route("/tts", methods=["GET", "POST"])
async def tts_endpoint(request: Request):
    """
    Universal TTS endpoint:
      - POST JSON: { "text": "...", "voice": "en-GB-MiaNeural" }
      - POST query: /tts?text=...&voice=...
      - GET  query: /tts?text=...
    Always returns the real URL (mp3 if Edge works, wav if fallback).
    """
    try:
        body = {}
        if request.method == "POST":
            try:
                body = await request.json()
                if not isinstance(body, dict):
                    body = {}
            except Exception:
                body = {}
        text: Optional[str]  = _first_nonempty(body.get("text") if body else None,
                                              request.query_params.get("text"))
        voice: Optional[str] = _first_nonempty(body.get("voice") if body else None,
                                              request.query_params.get("voice"))

        if not text:
            raise HTTPException(status_code=422, detail="Missing 'text'")

        url = await synthesize_to_static_url(text, reya=None, voice_override=voice)
        mime = "audio/wav" if url.lower().endswith(".wav") else "audio/mpeg"
        return JSONResponse({"url": url, "content_type": mime})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"detail": f"TTS failed: {e}"}, status_code=500)
