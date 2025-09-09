# backend/api.py
import os
import asyncio
import sys
import traceback
import importlib
from typing import Optional

from fastapi import FastAPI, Request, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from backend.llm_interface import (
    get_response,  # legacy path if you still use it
    get_structured_reasoning_prompt,
    query_ollama,
)
from backend.features.advanced_features import ContextualMemory
from backend.intent import recognize_intent
from backend.diagnostics import run_diagnostics
from backend.features.stackoverflow_search import search_stackoverflow
from backend.features.youtube_search import get_youtube_metadata
from backend.features.reddit_search import search_reddit
from backend.features.web_search import search_web
from backend.voice.edge_tts import (
    speak_with_voice_style,
    synthesize_to_static_url,
)

# -----------------------
# App & CORS
# -----------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    style=STYLES["oracle"],  # fine to keep this for text vibe
    voice="en-GB-MiaNeural",  # <-- your voice
    preset={"rate": "-10%", "pitch": "-5Hz", "volume": "+0%"}  # <-- your preset
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
# Health
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
# -----------------------
# TTS (fire-and-forget) - Local server playback (optional)
# -----------------------
@app.post("/speak")
async def speak_endpoint(data: SpeakRequest):
    text = (data.message or "").strip()
    if not text:
        return {"ok": False, "error": "Empty message"}
    asyncio.create_task(asyncio.to_thread(speak_with_voice_style, text, reya))
    return {"ok": True}

@app.on_event("startup")
async def _boot_banner():
    print("[REYA] Booting API… voice:", getattr(reya, "voice", None))

# -----------------------
# Chat (streaming by default; TTS JSON mode with ?speak=true)
# -----------------------
@app.post("/chat")
async def chat_endpoint(request: Request, speak: bool = Query(False)):
    body = await request.json()
    user_message = (body.get("message") or "").strip()

    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    # --- Diagnostics shortcut ---
    if "run diagnostics" in user_message.lower():
        report = await run_diagnostics(reya, memory, expected_ollama_model="mistral")
        text = report.as_text()

        async def stream_report():
            for line in text.split("\n"):
                yield line + "\n"
                await asyncio.sleep(0.03)

        # NOTE: this return MUST be OUTSIDE the async generator above
        return StreamingResponse(stream_report(), media_type="text/plain")

    # --- Normal REYA flow ---
    context = memory.get_context()
    prompt = get_structured_reasoning_prompt(user_message, context, reya=reya)
    full_response: str = query_ollama(prompt)  # sync call returns a string
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
# Existing utility routes (kept)
# -----------------------
@app.post("/reya/respond")
def respond_endpoint(data: MessageRequest):
    user_input = data.message
    intent = recognize_intent(user_input)
    context = memory.get_context()
    response = get_response(user_input, reya, context)
    memory.update_context(user_input, response)
    return {"response": response}

@app.post("/reya/logic")
def logic_layer(data: MessageRequest):
    context = memory.get_context()
    prompt = get_structured_reasoning_prompt(data.message, context, reya=reya)
    response = query_ollama(prompt)
    return {"response": response}

@app.post("/reya/project")
def multimodal_project_handler(data: MessageRequest):
    return {"response": f"Multimodal handler received: {data.message}"}

@app.get("/diagnostics")
async def diagnostics_json():
 report = await run_diagnostics(reya, memory, expected_ollama_model="mistral")
 return {
"summary": report.summary,
"checks": [
{"name": c.name, "ok": c.ok, "detail": c.detail, "warn": getattr(c, "warn", False)}
for c in report.checks
],
}
