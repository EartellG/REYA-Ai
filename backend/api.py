# backend/api.py
import os
import sys
import asyncio
import logging
import traceback
import importlib
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Query, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.routes.tickets import router as tickets_router 

# ---- Load environment early (backend/.env then project root .env)
ENV_HERE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_HERE)
load_dotenv(override=False)  # also picks up a root .env if present

# ---- Project paths / static
BACKEND_DIR = Path(__file__).resolve().parent
STATIC_DIR = BACKEND_DIR / "static"
(STATIC_DIR / "audio").mkdir(parents=True, exist_ok=True)

# ---- App + CORS
app = FastAPI(title="Reya Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Single, canonical static mount (matches edge_tts.py write location)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---- Personality / features / routers
from backend.reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from backend.features.advanced_features import ContextualMemory
from backend.features.advanced_features import PersonalizedKnowledgeBase
from backend.features.language_tutor import LanguageTutor

#----------------------
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
from .git_tools import router as git_tools

# LLM helpers
from backend.llm_interface import (
    get_response,
    get_structured_reasoning_prompt,
    query_ollama,
)
from backend.diagnostics import run_diagnostics

# TTS helpers
from backend.voice.edge_tts import (
    synth_to_bytes,
    synthesize_to_static_url,
    speak_with_voice_style,
)

# ---- Include routers (once)
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

# ---- Boot log
logging.getLogger("uvicorn.error").info(f"[REYA] Python: {sys.executable}")

# ---- Personality & memory
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

# -----------------------
# Health / Debug
# -----------------------
@app.get("/ping")
def ping():
    return {"message": "Pong from REYA backend!"}

@app.get("/")
async def root():
    return JSONResponse(content={"message": "REYA API is running!"})

@app.get("/status")
def status():
    return {"status": "REYA backend is running."}

@app.get("/debug/info")
def debug_info():
    info = {
        "cwd": os.getcwd(),
        "python": sys.version,
        "reya_voice": getattr(reya, "voice", None),
        "reya_preset": getattr(reya, "preset", None),
        "static_dir": str(STATIC_DIR),
    }
    try:
        et = importlib.import_module("backend.voice.edge_tts")
        info["edge_tts_module"] = getattr(et, "__file__", "unknown")
        info["edge_exports"] = [n for n in dir(et) if n.startswith(("synthesize_", "synth_", "speak_"))]
        info["edge_signature"] = getattr(et, "SIGNATURE", "(no signature)")
    except Exception as e:
        info["edge_import_error"] = repr(e)
        info["edge_traceback"] = traceback.format_exc(limit=2)
    return info

@app.on_event("startup")
async def _boot_banner():
    print("[REYA] Booting API… voice:", getattr(reya, "voice", None))

# -----------------------
# Speak (server-side playback, fire-and-forget)
# -----------------------
class SpeakRequestModel:
    message: str

@app.post("/speak")
async def speak_endpoint(data: dict):
    text = (data.get("message") or "").strip()
    if not text:
        return {"ok": False, "error": "Empty message"}
    # Run in background thread to avoid blocking event loop
    asyncio.create_task(asyncio.to_thread(speak_with_voice_style, text, reya))
    return {"ok": True}

# -----------------------
# Chat (streaming; optional speak)
# -----------------------
@app.post("/chat")
async def chat_endpoint(request: Request, speak: bool = Query(False)):
    body = await request.json()
    user_message = (body.get("message") or "").strip()
    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    # Quick diagnostics trigger
    if "run diagnostics" in user_message.lower():
        report = await run_diagnostics(reya, memory)
        text = report.as_text()

        async def stream_report():
            for line in text.split("\n"):
                yield line + "\n"
                await asyncio.sleep(0.03)

        return StreamingResponse(stream_report(), media_type="text/plain")

    # Normal flow
    context = memory.get_context()
    prompt = get_structured_reasoning_prompt(user_message, context, reya=reya)
    full_response: str = await asyncio.to_thread(query_ollama, prompt)
    memory.remember(user_message, full_response)

    if speak:
        try:
            audio_url = await synthesize_to_static_url(full_response, reya)
        except Exception as e:
            return JSONResponse(
                {"text": full_response, "audio_url": None, "error": f"TTS failed: {e}"},
                status_code=200,
            )
        return JSONResponse({"text": full_response, "audio_url": audio_url}, status_code=200)

    async def generate_stream():
        for word in full_response.split():
            yield f"{word} "
            await asyncio.sleep(0.05)

    return StreamingResponse(generate_stream(), media_type="text/plain")

# -----------------------
# Pure TTS for frontend (returns /static/audio/<uuid>.mp3|.wav)
# -----------------------
@app.post("/tts")
async def tts_endpoint(payload: dict = Body(...)):
    text = (payload.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "Empty text"}
    url = await synthesize_to_static_url(text, reya)
    return {"ok": True, "audio_url": url}

# Direct bytes test (useful for tutor buttons)
@app.get("/voice/test")
async def voice_test(
    text: str = Query("Hello from REYA"),
    voice: str = Query("en-GB-SoniaNeural"),
    rate: str = Query("+0%"),
    volume: str = Query("+0%"),
):
    audio, meta = await synth_to_bytes(text, voice=voice, rate=rate, volume=volume)
    fmt = (meta.get("format") or "").lower()
    media = "audio/mpeg" if "mp3" in fmt or "mpeg" in fmt else "audio/wav"
    return Response(
        content=audio,
        media_type=media,
        headers={
            "X-REYA-TTS-Engine": meta.get("engine", ""),
            "X-REYA-TTS-Voice": meta.get("voice", ""),
        },
    )

# -----------------------
# Language Tutor
# -----------------------
@app.post("/tutor/start")
async def tutor_start(payload: dict):
    lang = payload.get("language", "Japanese")
    level = payload.get("level", "beginner")
    msg = tutor.start(lang, level)
    return {"message": msg}

@app.get("/tutor/resume")
async def tutor_resume(language: str):
    return {"message": tutor.resume(language)}

@app.get("/tutor/next")
async def tutor_next(language: str):
    return {"message": tutor.next_lesson(language)}

@app.get("/tutor/progress")
async def tutor_progress(language: str):
    return tutor.get_progress(language)

@app.get("/tutor/quiz")
async def tutor_quiz(language: str):
    q = tutor.quiz_vocabulary(language)
    if not q:
        return JSONResponse({"message": "no_vocab"}, status_code=404)
    return q

@app.post("/tutor/check")
async def tutor_check(payload: dict):
    qp = payload.get("payload", {})
    ua = payload.get("user_answer", "")
    ok, msg = tutor.check_answer(qp, ua)
    return {"ok": ok, "message": msg}

@app.get("/tutor/test_voice")
async def tutor_test_voice(
    text: str = Query("こんにちは — Hello"),
    voice: str = Query("ja-JP-NanamiNeural"),
):
    audio, meta = await synth_to_bytes(text, voice=voice)
    fmt = (meta.get("format") or "").lower()
    media = "audio/mpeg" if "mp3" in fmt or "mpeg" in fmt else "audio/wav"
    return Response(
        content=audio,
        media_type=media,
        headers={
            "X-REYA-TTS-Engine": meta.get("engine", ""),
            "X-REYA-TTS-Voice": meta.get("voice", ""),
        },
    )

# -----------------------
# Knowledge Base (simple)
# -----------------------
@app.get("/kb/list")
async def kb_list(category: str):
    return kb.search_knowledge("", [category])

@app.get("/kb/search")
async def kb_search(query: str, category: str):
    return kb.search_knowledge(query, [category])

# -----------------------
# Diagnostics for UI card
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
