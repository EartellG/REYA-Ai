# backend/api.py
import os
import asyncio
import sys
import traceback
import importlib
from typing import Optional

from fastapi import FastAPI, Request, Query, Body
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from backend.llm_interface import (
    get_response,  # legacy high-level helper
    get_structured_reasoning_prompt,
    query_ollama,
)
from backend.features.advanced_features import ContextualMemory
from backend.features.advanced_features import PersonalizedKnowledgeBase
from backend.features.language_tutor import LanguageTutor
from backend.intent import recognize_intent
from backend.diagnostics import run_diagnostics
from backend.voice.edge_tts import (
    speak_with_voice_style,
    synthesize_to_static_url,   # ✅ single import
)
# Optional: other features (kept for future use)
# from backend.features.stackoverflow_search import search_stackoverflow
# from backend.features.youtube_search import get_youtube_metadata
# from backend.features.reddit_search import search_reddit
# from backend.features.web_search import search_web

# -----------------------
# App & CORS
# -----------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # consider restricting in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------
# Static files for audio
# -----------------------
os.makedirs("static/audio", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------
# Personality & Memory
# -----------------------
reya = ReyaPersonality(
    traits=[TRAITS["stoic"], TRAITS["playful"]],
    mannerisms=[MANNERISMS["sassy"], MANNERISMS["meta_awareness"]],
    style=STYLES["oracle"],                 # text vibe
    voice="en-GB-MiaNeural",                # TTS voice
    preset={"rate": "+12%", "pitch": "-5Hz", "volume": "+0%"},
)
memory = ContextualMemory()

# -----------------------
# Models
# -----------------------
class MessageRequest(BaseModel):
    message: str

class SpeakRequest(BaseModel):
    message: str

class ChatRequest(BaseModel):
    message: str

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
        "sys_path_first": sys.path[:3],
        "reya_voice": getattr(reya, "voice", None),
        "reya_preset": getattr(reya, "preset", None),
    }
    try:
        et = importlib.import_module("backend.voice.edge_tts")
        info["edge_tts_module"] = getattr(et, "__file__", "unknown")
        info["edge_tts_exports"] = [n for n in dir(et) if n.startswith(("synthesize_", "speak_"))]
        info["edge_tts_signature"] = getattr(et, "SIGNATURE", "(no signature)")
    except Exception as e:
        info["edge_tts_import_error"] = repr(e)
        info["edge_tts_traceback"] = traceback.format_exc(limit=2)
    return info

@app.on_event("startup")
async def _boot_banner():
    print("[REYA] Booting API… voice:", getattr(reya, "voice", None))

# -----------------------
# TTS (fire-and-forget local playback)
# -----------------------
@app.post("/speak")
async def speak_endpoint(data: SpeakRequest):
    text = (data.message or "").strip()
    if not text:
        return {"ok": False, "error": "Empty message"}
    asyncio.create_task(asyncio.to_thread(speak_with_voice_style, text, reya))
    return {"ok": True}

# -----------------------
# Chat (streaming by default; optional speak=true JSON mode)
# -----------------------
@app.post("/chat")
async def chat_endpoint(request: Request, speak: bool = Query(False)):
    body = await request.json()
    user_message = (body.get("message") or "").strip()

    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    # --- Diagnostics shortcut ---
    if "run diagnostics" in user_message.lower():
        # Let diagnostics auto-detect required model (no hardcode)
        report = await run_diagnostics(reya, memory)
        text = report.as_text()

        async def stream_report():
            for line in text.split("\n"):
                yield line + "\n"
                await asyncio.sleep(0.03)

        return StreamingResponse(stream_report(), media_type="text/plain")

    # --- Normal REYA flow ---
    context = memory.get_context()
    prompt = get_structured_reasoning_prompt(user_message, context, reya=reya)

    # Offload Ollama call to a thread to avoid blocking event loop
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
# Legacy / utility endpoints
# -----------------------
@app.post("/reya/respond")
def respond_endpoint(data: MessageRequest):
    user_input = data.message
    intent = recognize_intent(user_input)  # currently unused but kept
    context = memory.get_context()
    # Fix arg order to match llm_interface.get_response(user_input, reya, history)
    response = get_response(user_input, reya, context)
    memory.remember(user_input, response)
    return {"response": response, "intent": intent}

@app.post("/reya/logic")
def logic_layer(data: MessageRequest):
    context = memory.get_context()
    prompt = get_structured_reasoning_prompt(data.message, context, reya=reya)
    response = query_ollama(prompt)
    return {"response": response}

@app.post("/reya/project")
def multimodal_project_handler(data: MessageRequest):
    return {"response": f"Multimodal handler received: {data.message}"}

# -----------------------
# Pure TTS for frontend
# -----------------------
@app.post("/tts")
async def tts_endpoint(payload: dict = Body(...)):
    text = (payload.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "Empty text"}
    url = await synthesize_to_static_url(text, reya)
    return {"ok": True, "audio_url": url}

# -----------------------
# Diagnostics JSON for UI card
# -----------------------
@app.get("/diagnostics")
async def diagnostics_json():
    report = await run_diagnostics(reya, memory)  # auto model detect
    return {
        "summary": report.summary,
        "checks": [
            {"name": c.name, "ok": c.ok, "detail": c.detail, "warn": getattr(c, "warn", False)}
            for c in report.checks
        ],
    }

##Personalized Knowledge
kb = PersonalizedKnowledgeBase()
@app.post("/kb/import")
async def kb_import(payload: dict):
    category = payload.get("category")
    notes = payload.get("notes")  # list of {title, content, tags?, source?}
    if not category or not isinstance(notes, list):
        return JSONResponse({"ok": False, "error": "category and notes[] required"}, status_code=400)
    ids = kb.add_bulk_notes(category, notes)
    return {"ok": True, "count": len(ids), "ids": ids}


##Language Tutor
tutor = LanguageTutor(memory)
@app.get("/tutor/progress")
def tutor_progress(language: str = "Japanese"):
    return tutor.get_progress(language)

@app.post("/tutor/start")
def tutor_start(payload: dict):
    language = (payload.get("language") or "Japanese").strip()
    level = (payload.get("level") or "beginner").strip()
    resume = bool(payload.get("resume") or False)
    msg = tutor.start(language, level, resume=resume)
    return {"message": msg}

@app.get("/tutor/resume")
def tutor_resume(language: str = "Japanese"):
    return {"message": tutor.resume(language)}

@app.get("/tutor/next")
def tutor_next(language: str = "Japanese"):
    return {"message": tutor.next_lesson(language)}

@app.get("/tutor/quiz")
def tutor_quiz(language: str = "Japanese"):
    q = tutor.quiz_vocabulary(language)
    if not q:
        return {"ok": False, "error": "No vocabulary yet."}
    return {"ok": True, "quiz": q}

@app.post("/tutor/answer")
def tutor_answer(payload: dict):
    quiz = payload.get("quiz")
    ans = payload.get("answer")
    ok, msg = tutor.check_answer(quiz or {}, ans or "")
    return {"ok": ok, "message": msg}
