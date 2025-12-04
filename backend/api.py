# backend/api.py
"""
Cleaned & upgraded REYA API
- Whisper.cpp STT as primary (accepts multipart/form-data 'audio' file)
- Text fallback when no audio provided
- Uses get_response(...) as REYA brain (personality + reasoning)
- Optional TTS output via speech_manager (OpenTTS/Coqui -> Silero fallback)
- Streaming text responses to frontend
"""

import os
import sys
import asyncio
import logging
import traceback
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Query, Body, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

# load env early so submodules can read env flags during hot-reload
ENV_HERE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_HERE)
load_dotenv(override=False)

# project paths
BACKEND_DIR = Path(__file__).resolve().parent
STATIC_DIR = BACKEND_DIR / "static"
AUDIO_DIR = STATIC_DIR / "audio"
STT_INPUT_DIR = STATIC_DIR / "stt_input"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
STT_INPUT_DIR.mkdir(parents=True, exist_ok=True)

# basic app + CORS
app = FastAPI(title="REYA Backend (cleaned)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# static mount
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---- imports that rely on env / project layout
from backend.reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from backend.features.advanced_features import ContextualMemory, PersonalizedKnowledgeBase
from backend.features.language_tutor import LanguageTutor

from backend.llm_interface import (
    get_response,  # <--- full REYA brain (selected option B)
    get_structured_reasoning_prompt,
    query_ollama,
)

from backend.diagnostics import run_diagnostics

# TTS helpers (edge/azure + file helpers)
from backend.voice.edge_tts import synth_to_bytes, synthesize_to_static_url, speak_with_voice_style, engine_status

# Speech manager wrapper (OpenTTS/Coqui -> Silero fallback)
from backend.voice.speech_manager import synthesize_tts

# Whisper.cpp wrapper (local exe)
from backend.stt.whisper_cpp import transcribe_whisper_cpp

# project routers (keep your routes)
from backend.routes.tickets import router as tickets_router
from backend.routes.settings import router as settings_router
from backend.routes.reviewer_prefill import router as reviewer_prefill_router
from backend.routes.voice_router import router as voice_router
from backend.routes.roles_reviewer_lint import router as reviewer_lint_router
from backend.routes.tts import router as tts_router
from backend.routes.tts import debug_router as tts_debug_router
from backend.routes.tts_vocab import router as tts_vocab_router
from backend.routes.roles_pm import router as roles_pm_router
from backend.routes.roles_coder import router as roles_coder_router
from backend.routes.roles_reviewer import router as roles_reviewer_router
from backend.routes.roles_fixer import router as roles_fixer_router
from backend.routes.roles_monetizer import router as roles_monetizer_router
from backend.routes.wireframes import router as wireframes_router
from backend.project_tools import router as project_tools
from backend.git_tools import router as git_tools
from backend.routes.workspace import router as workspace_router

# register routers (existing setup)
app.include_router(git_tools)
app.include_router(project_tools)
app.include_router(settings_router)
app.include_router(voice_router)
app.include_router(tts_router)
app.include_router(tts_debug_router)
app.include_router(tts_vocab_router)
app.include_router(roles_pm_router)
app.include_router(roles_coder_router)
app.include_router(roles_reviewer_router)
app.include_router(roles_fixer_router)
app.include_router(roles_monetizer_router)
app.include_router(wireframes_router)
app.include_router(tickets_router)
app.include_router(reviewer_prefill_router)
app.include_router(reviewer_lint_router)
app.include_router(workspace_router)

# logging
logging.getLogger("uvicorn.error").info(f"[REYA] Python: {sys.executable}")

# personality & memory singletons
reya = ReyaPersonality(
    traits=[TRAITS["stoic"], TRAITS["playful"]],
    mannerisms=[MANNERISMS["sassy"], MANNERISMS["meta_awareness"]],
    style=STYLES["oracle"],
    voice="en-GB-SoniaNeural",
    preset={"rate": "+14%", "pitch": "-5Hz", "volume": "+0%"},
)
memory = ContextualMemory()
kb = PersonalizedKnowledgeBase()
tutor = LanguageTutor(memory)

# health endpoints
@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/")
async def root():
    return JSONResponse({"message": "REYA API is running", "engine": engine_status()})

@app.get("/debug/info")
def debug_info():
    info = {
        "cwd": os.getcwd(),
        "python": sys.version,
        "reya_voice": getattr(reya, "voice", None),
        "static_dir": str(STATIC_DIR),
    }
    try:
        et = __import__("backend.voice.edge_tts", fromlist=["*"])
        info["edge_tts_module"] = getattr(et, "__file__", "unknown")
    except Exception as e:
        info["edge_error"] = repr(e)
    return info

@app.on_event("startup")
async def _boot_banner():
    print("[REYA] Booting API… voice:", getattr(reya, "voice", None))


# -----------------------
# Helper: stream generator (word-by-word)
# -----------------------
async def _stream_text(text: str, delay: float = 0.03):
    for word in text.split():
        yield f"{word} "
        await asyncio.sleep(delay)


# -----------------------
# Core /chat endpoint
# - Accepts either:
#   * multipart/form-data with key 'audio' (file) -> transcribe via Whisper.cpp
#   * or JSON body { "message": "..." } -> uses message directly
# - Uses get_response(...) as the REYA brain (option B)
# - Optional query param speak=true to also produce audio (Coqui via OpenTTS -> Silero fallback)
# -----------------------
@app.post("/chat")
async def chat_endpoint(
    request: Request,
    speak: bool = Query(False),
):
    """
    Upgraded chat pipeline:
    - If multipart with 'audio' file: save -> run Whisper.cpp -> get transcribed_text
    - Else: use JSON body 'message'
    - Feed to get_response(...) which should apply REYA personality, reasoning, and memory
    - If speak=True, attempt to produce an audio file (synthesize_tts) and return audio_url + text
    - Otherwise return a streaming text response
    """
    # 1) Accept either audio upload or JSON text
    content_type = request.headers.get("content-type", "") or ""
    user_message = ""
    transcribed = None

    try:
        if "multipart/form-data" in content_type.lower():
            form = await request.form()
            audio_file = form.get("audio")  # UploadFile
            if not audio_file:
                raise HTTPException(status_code=400, detail="No 'audio' file in form data.")
            if isinstance(audio_file, UploadFile):
                # Save upload to disk for Whisper.cpp
                filename_safe = f"stt_{uuid4().hex}_{os.path.basename(audio_file.filename)}"
                save_path = STT_INPUT_DIR / filename_safe
                with open(save_path, "wb") as f:
                    content = await audio_file.read()
                    f.write(content)
                # Run whisper.cpp transcriber (blocking subprocess) in thread
                try:
                    transcribed = await asyncio.to_thread(transcribe_whisper_cpp, str(save_path))
                    user_message = transcribed.strip()
                except Exception as e:
                    # fallback: try to decode with SpeechRecognition (if present) or error back
                    raise HTTPException(status_code=500, detail=f"Whisper.cpp transcription failed: {e}")
            else:
                raise HTTPException(status_code=400, detail="Invalid audio upload.")
        else:
            # JSON path
            body = await request.json()
            user_message = (body.get("message") or "").strip()
            if not user_message:
                raise HTTPException(status_code=400, detail="Missing 'message' in request body.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing request: {e}")

    # 2) Diagnostics trigger
    if "run diagnostics" in user_message.lower():
        report = await run_diagnostics(reya, memory)
        text = report.as_text()
        return StreamingResponse(_stream_text(text, delay=0.01), media_type="text/plain")

    # 3) Build context & call REYA brain
    try:
        context = memory.get_context()
        # get_response is expected to return a dict or string. Adjust if your signature differs.
        # Example assumed signature: get_response(message: str, reya, memory) -> str
        reya_response = await asyncio.to_thread(get_response, user_message, reya, memory)
        if isinstance(reya_response, dict):
            full_text = reya_response.get("text") or reya_response.get("response") or ""
            metadata = reya_response.get("meta", {})
        else:
            full_text = str(reya_response)
            metadata = {}
    except Exception as e:
        tb = traceback.format_exc(limit=4)
        logging.getLogger("uvicorn.error").exception("LLM failure")
        raise HTTPException(status_code=500, detail=f"REYA brain failed: {e}\n{tb}")

    # 4) Remember interaction
    try:
        memory.remember(user_message, full_text)
    except Exception:
        logging.getLogger("uvicorn.error").warning("Memory remember failed", exc_info=True)

    # 5) If speak requested -> synthesize audio and return JSON with audio_url + text
    if speak:
        try:
            # prefer speech_manager synthesize_tts (OpenTTS -> Silero fallback)
            audio_local_path = await asyncio.to_thread(synthesize_tts, full_text, "reya_chat_output.wav")
            # audio_local_path is local fs path under static/audio -> return relative url
            rel = Path(audio_local_path).resolve().relative_to(STATIC_DIR.resolve()).as_posix()
            audio_url = f"/static/{rel}"
            return JSONResponse({"text": full_text, "audio_url": audio_url})
        except Exception as e:
            # fallback to edge_tts synthesize_to_static_url if available
            try:
                audio_url = await synthesize_to_static_url(full_text, reya)
                return JSONResponse({"text": full_text, "audio_url": audio_url})
            except Exception as e2:
                logging.getLogger("uvicorn.error").exception("TTS failed")
                return JSONResponse({"text": full_text, "audio_url": None, "error": f"TTS failed: {e} / {e2}"})

    # 6) Otherwise stream text back
    return StreamingResponse(_stream_text(full_text), media_type="text/plain")


# -----------------------
# Simple TTS endpoint (explicit)
# -----------------------
@app.post("/tts")
async def tts_endpoint(payload: dict = Body(...)):
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")
    try:
        # Try speech_manager first (OpenTTS -> Silero)
        audio_local_path = await asyncio.to_thread(synthesize_tts, text, "reya_tts_out.wav")
        rel = Path(audio_local_path).resolve().relative_to(STATIC_DIR.resolve()).as_posix()
        return {"ok": True, "audio_url": f"/static/{rel}"}
    except Exception as e:
        # fallback to edge_tts
        try:
            url = await synthesize_to_static_url(text, reya)
            return {"ok": True, "audio_url": url}
        except Exception as e2:
            logging.getLogger("uvicorn.error").exception("TTS failed")
            raise HTTPException(status_code=500, detail=f"TTS failed: {e} / {e2}")


# -----------------------
# Diagnostics JSON for UI
# -----------------------
@app.get("/diagnostics")
async def diagnostics_json():
    report = await run_diagnostics(reya, memory)
    return {
        "summary": report.summary,
        "checks": [
            {"name": c.name, "ok": c.ok, "detail": c.detail, "warn": getattr(c, "warn", False)}
            for c in report.checks
        ],
    }
