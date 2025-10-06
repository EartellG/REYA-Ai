from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from typing import Optional
from backend.voice.edge_tts import synthesize_to_static_url, synth_to_bytes
import os

router = APIRouter(tags=["tts"])
debug_router = APIRouter(prefix="/tts", tags=["tts-debug"])

def _first_nonempty(*vals):
    for v in vals:
        if v is not None and str(v).strip():
            return str(v)
    return None


@debug_router.get("/debug_status")
def tts_debug_status():
    return {
        "azure_present": bool(os.getenv("AZURE_SPEECH_KEY")) and bool(os.getenv("AZURE_SPEECH_REGION")),
        "region": os.getenv("AZURE_SPEECH_REGION"),
        "edge_enabled": os.getenv("REYA_TTS_EDGE_ENABLED", "0"),
        "fallback_allowed": os.getenv("REYA_TTS_ALLOW_FALLBACK", "0"),
    }
@router.api_route("/tts", methods=["GET", "POST"])
async def tts_endpoint(request: Request, bytes: int = Query(0)):
    """
    - bytes=1 -> returns audio bytes (Edge-only)
    - default -> returns static URL (mp3 file) as before
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
        text: Optional[str]  = _first_nonempty(body.get("text") if body else None, request.query_params.get("text"))
        voice: Optional[str] = _first_nonempty(body.get("voice") if body else None, request.query_params.get("voice"))

        if not text:
            raise HTTPException(status_code=422, detail="Missing 'text'")

        if bytes:
            audio, meta = await synth_to_bytes(text, voice=voice or "en-GB-SoniaNeural")
            media = meta.get("format", "audio/mpeg")
            return Response(content=audio, media_type=media, headers={
                "X-REYA-TTS-Engine": meta.get("engine",""),
                "X-REYA-TTS-Voice": meta.get("voice",""),
            })

        url = await synthesize_to_static_url(text, reya=None, voice_override=voice)
        mime = "audio/wav" if url.lower().endswith(".wav") else "audio/mpeg"
        return JSONResponse({"url": url, "content_type": mime})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"detail": f"TTS failed: {e}"}, status_code=500)
