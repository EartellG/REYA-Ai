# backend/main.py
from __future__ import annotations
import os
import sys
import asyncio
import logging
import traceback
import importlib
import tempfile
import threading
import random
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, cast

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Query, Body, Response, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# -------------------------------------------------------------------------
# Load .env early (backend/.env then project root .env)
# -------------------------------------------------------------------------
ENV_HERE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_HERE)
load_dotenv(override=False)

# -------------------------------------------------------------------------
# Project paths / static
# -------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
STATIC_DIR = BACKEND_DIR / "static"
AUDIO_DIR = STATIC_DIR / "audio"
(STATIC_DIR / "audio").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "stt_output").mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# REYA core imports (features, llm helpers, tts, stt)
# -------------------------------------------------------------------------
# personality / features
from backend.reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from backend.features.advanced_features import ContextualMemory, PersonalizedKnowledgeBase
from backend.features.language_tutor import LanguageTutor

# helper features used by core
from backend.features.logic_engine import evaluate_logic
from backend.features.stackoverflow_search import search_stackoverflow
from backend.features.youtube_search import get_youtube_metadata
from backend.features.reddit_search import search_reddit
from backend.features.web_search import search_web
from backend.intent import recognize_intent
from backend.utils.translate import translate_to_english
from backend.utils.sanitize import sanitize_response
from backend.features.identity import IdentityStore

# llm interface (query_ollama expected to be sync/blocking or wrapped in thread)
from backend.llm_interface import get_structured_reasoning_prompt, query_ollama

# diagnostics
from backend.diagnostics import run_diagnostics

# tts & speech manager
from backend.voice.edge_tts import (
    synth_to_bytes,
    synthesize_to_static_url,
    speak_with_voice_style,
    engine_status as tts_engine_status,
)
from backend.voice.speech_manager import synthesize_tts  # wrapper that can hit OpenTTS / Silero

# stt (whisper.cpp wrapper)
from backend.stt.whisper_cpp import transcribe_whisper_cpp

# wake-word / stt utilities (the voice/stt.py you updated)
from backend.voice.stt import wait_for_wake_word, listen_for_command

# -------------------------------------------------------------------------
# Logging / boot info
# -------------------------------------------------------------------------
logging.getLogger("uvicorn.error").info(f"[REYA] Python: {sys.executable}")

# -------------------------------------------------------------------------
# Reya personality & memory initialization
# -------------------------------------------------------------------------
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

# -------------------------------------------------------------------------
# Core Brain (refactored/clean)
# -------------------------------------------------------------------------
class ReyaCore:
    def __init__(self):
        self.memory = memory
        self.proactive = importlib.import_module("backend.features.advanced_features").ProactiveAssistance(self.memory)
        self.automation = importlib.import_module("backend.features.advanced_features").TaskAutomation()
        self.emotions = importlib.import_module("backend.features.advanced_features").EmotionalIntelligence()
        self.tutor = tutor
        self.identity = IdentityStore(self.memory)

    @staticmethod
    def _parse_language_level(text: str) -> Tuple[Optional[str], str]:
        t = text.lower()
        lang: Optional[str] = None
        if "japanese" in t:
            lang = "Japanese"
        elif "mandarin" in t:
            lang = "Mandarin"
        level = "beginner"
        if "intermediate" in t:
            level = "intermediate"
        elif "advanced" in t:
            level = "advanced"
        return lang, level

    @staticmethod
    def _try_parse_identity_command(tlower: str) -> Optional[Tuple[str, Optional[str]]]:
        import re
        name: Optional[str] = None
        alias: Optional[str] = None
        m1 = re.search(r"\bmy name is\s+([a-z][a-z\s.'-]{1,60})", tlower)
        if m1:
            name = m1.group(1).strip().title()
        m2 = re.search(r"\bcall me\s+([a-z][a-z\s.'-]{1,60})", tlower)
        if m2:
            alias = m2.group(1).strip().title()
        if name or alias:
            first = cast(str, (name or alias))
            return (first, alias)
        return None

    def handle_text(self, raw_input: str) -> str:
        if not raw_input or not raw_input.strip():
            return ""
        user_input = raw_input.strip()
        translated = translate_to_english(user_input) or user_input
        tlower = translated.lower()

        ident = self._try_parse_identity_command(tlower)
        if ident:
            name, alias = ident
            self.identity.set_primary_user(name=name, alias=alias, is_admin=True)

        # Identity query
        if "who am i" in tlower or "who are you" in tlower:
            pu = self.identity.get_primary_user()
            me = "Reya"
            you = (pu.get("alias") or pu.get("name")) if pu else "friend"
            return sanitize_response(f"I am {me}. You are {you}.")

        # Short-circuits
        if tlower in {"quit", "exit", "bye"}:
            return "Goodbye!"

        # Language tutor quick commands
        if "teach me japanese" in tlower or "teach me mandarin" in tlower:
            lang, level = self._parse_language_level(tlower)
            if lang:
                lesson = self.tutor.start(language=lang, level=level)
                self.memory.remember(f"{lang} {level} lesson", lesson)
                return lesson

        if "quiz me in japanese" in tlower or "quiz me in mandarin" in tlower:
            lang = "Japanese" if "japanese" in tlower else "Mandarin"
            return self.tutor.quiz_vocabulary(lang)  # type: ignore

        emo = self.emotions.analyze_and_respond(translated)
        if emo:
            return emo

        intent = recognize_intent(translated)
        tip = self.proactive.suggest(translated)

        automated = self.automation.handle(translated)
        if automated:
            self.memory.remember(translated, automated)
            return f"{tip + ' ' if tip else ''}{automated}".strip()

        # Logic engine quick check
        if any(k in tlower for k in [" and ", " or ", " not ", "true", "false"]):
            result = evaluate_logic(translated)
            return f"{tip + ' ' if tip else ''}The logic result is: {result}"

        # Search / helper features
        if "stackoverflow" in tlower or "code" in tlower:
            ans = search_stackoverflow(translated)
            self.memory.remember(translated, ans)
            return f"{tip + ' ' if tip else ''}{ans}".strip()

        if "youtube" in tlower:
            meta = get_youtube_metadata(translated)
            if meta and meta.get("title"):
                return f"{tip + ' ' if tip else ''}The title is: {meta['title']}"
            return "I couldn't fetch YouTube data."

        if "reddit" in tlower:
            threads = search_reddit(translated)
            if threads:
                return f"{tip + ' ' if tip else ''}Here's a Reddit post: {threads[0]}"
            return "No relevant Reddit threads found."

        if "search" in tlower or "look up" in tlower:
            res = search_web(translated)
            self.memory.remember(translated, res)
            return f"{tip + ' ' if tip else ''}{res}".strip()

        # Default LLM path
        context = self.memory.get_recent_conversations()
        prompt = get_structured_reasoning_prompt(translated, context, reya=reya)
        # query_ollama may be blocking — run in thread to avoid blocking event loop
        response: str = asyncio.run(asyncio.to_thread(query_ollama, prompt))
        self.memory.remember(user_input, response)
        return sanitize_response(response.strip())

# create core instance
core = ReyaCore()

# -------------------------------------------------------------------------
# Routers import (same list you had in api.py)
# -------------------------------------------------------------------------
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
from backend.routes.tickets import router as tickets_router
from backend.routes.reviewer_prefill import router as reviewer_prefill_router

# -------------------------------------------------------------------------
# FastAPI app creation (single app for everything)
# -------------------------------------------------------------------------
app = FastAPI(title="Reya Unified Backend", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# include routers
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
app.include_router(reviewer_lint_router)
app.include_router(workspace_router)

# -------------------------------------------------------------------------
# Small utilities & wake replies
# -------------------------------------------------------------------------
WAKE_REPLIES = [
    "How may I assist you?",
    "Yes?",
    "I'm listening.",
    "What can I do for you?",
    "At your service.",
    "Go ahead — I'm all ears.",
]

def random_wake_reply() -> str:
    return random.choice(WAKE_REPLIES)

# -------------------------------------------------------------------------
# Health / Debug endpoints
# -------------------------------------------------------------------------
@app.get("/ping")
def ping():
    return {"message": "Pong from REYA backend!"}

@app.get("/")
def root():
    return {"ok": True, "service": "reya-backend", "version": "4.0", "tts_engine": tts_engine_status().get("engine_choice")}

@app.get("/debug/info")
def debug_info():
    info = {
        "cwd": os.getcwd(),
        "python": sys.version,
        "reya_voice": getattr(reya, "voice", None),
        "reya_preset": getattr(reya, "preset", None),
        "static_dir": str(STATIC_DIR),
        "tts": tts_engine_status(),
    }
    return info

# -------------------------------------------------------------------------
# Speak (fire-and-forget server-side playback)
# -------------------------------------------------------------------------
@app.post("/speak")
async def speak_endpoint(data: dict = Body(...)):
    text = (data.get("message") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")
    # run synth/play in background so API returns quickly
    asyncio.create_task(asyncio.to_thread(speak_with_voice_style, text, reya))
    return {"ok": True}

# -------------------------------------------------------------------------
# TTS endpoint (returns URL to static audio file)
# -------------------------------------------------------------------------
@app.post("/tts")
async def tts_endpoint(payload: dict = Body(...)):
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")
    url = await synthesize_to_static_url(text, reya)
    return {"ok": True, "audio_url": url}

# -------------------------------------------------------------------------
# Chat endpoint — accepts JSON {message:"..."} OR multipart audio upload
# Whisper.cpp runs by default when an audio file is provided.
# -------------------------------------------------------------------------
@app.post("/chat")
async def chat_endpoint(request: Request, speak: bool = Query(False), audio: Optional[UploadFile] = File(None)):
    """
    If `audio` file is provided: run Whisper.cpp transcription first (default).
    Otherwise expects JSON body with {"message": "..."}.
    If speak=True, attach TTS audio_url in the response.
    """
    # 1) Handle audio upload path (Whisper.cpp primary)
    user_message: Optional[str] = None
    if audio is not None:
        # write to temp file
        try:
            suffix = Path(audio.filename).suffix or ".wav"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_path = tmp.name
            tmp.write(await audio.read())
            tmp.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded audio: {e}")

        # try whisper.cpp first
        try:
            transcription = transcribe_whisper_cpp(tmp_path)
            user_message = transcription.strip()
        except Exception as e:
            # log and fall back to other STT options if you implement them
            logging.getLogger("uvicorn.error").warning(f"Whisper.cpp failed: {e}")
            # try speech_recognition fallback (if configured) — not implemented here
            user_message = ""  # treat as empty and handle below

        # cleanup temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    # 2) If no audio (or transcription empty), read JSON payload
    if not user_message:
        body = await request.json()
        user_message = (body.get("message") or "").strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message or empty transcription")

    # special trigger: run diagnostics if asked
    if "run diagnostics" in user_message.lower():
        report = await run_diagnostics(reya, memory)
        text = report.as_text()
        async def stream_report():
            for line in text.split("\n"):
                yield line + "\n"
                await asyncio.sleep(0.02)
        return StreamingResponse(stream_report(), media_type="text/plain")

    # Normal flow: structured prompt -> model
    context = memory.get_context()
    prompt = get_structured_reasoning_prompt(user_message, context, reya=reya)
    # run LLM in thread to avoid blocking
    full_response = await asyncio.to_thread(query_ollama, prompt)
    memory.remember(user_message, full_response)

    if speak:
        try:
            audio_url = await synthesize_to_static_url(full_response, reya)
        except Exception as e:
            # fallback: produce local silero file via speech_manager
            logging.getLogger("uvicorn.error").warning(f"TTS synth_to_static_url failed: {e}; attempting speech_manager fallback")
            try:
                audio_path = synthesize_tts(full_response, filename=f"reya_{os.urandom(4).hex()}.wav")
                # convert file path to /static/ path if under STATIC_DIR
                audio_url = "/" + os.path.relpath(audio_path, STATIC_DIR).replace("\\", "/")
            except Exception as e2:
                logging.getLogger("uvicorn.error").error(f"All TTS fallbacks failed: {e2}")
                audio_url = None
        return JSONResponse({"text": full_response, "audio_url": audio_url}, status_code=200)

    # stream text back word-by-word to the frontend (keeps compatibility with streaming UI)
    async def generate_stream():
        for word in str(full_response).split():
            yield f"{word} "
            await asyncio.sleep(0.03)
    return StreamingResponse(generate_stream(), media_type="text/plain")

# -------------------------------------------------------------------------
# Language Tutor endpoints (thin wrappers)
# -------------------------------------------------------------------------
@app.post("/tutor/start")
async def tutor_start(payload: dict = Body(...)):
    lang = payload.get("language", "Japanese")
    level = payload.get("level", "beginner")
    msg = tutor.start(lang, level)
    return {"message": msg}

@app.get("/tutor/resume")
def tutor_resume(language: str):
    return {"message": tutor.resume(language)}

@app.get("/tutor/next")
def tutor_next(language: str):
    return {"message": tutor.next_lesson(language)}

@app.get("/tutor/progress")
def tutor_progress(language: str):
    return tutor.get_progress(language)

@app.get("/tutor/quiz")
def tutor_quiz(language: str):
    q = tutor.quiz_vocabulary(language)
    if not q:
        return JSONResponse({"message": "no_vocab"}, status_code=404)
    return q

@app.post("/tutor/check")
def tutor_check(payload: dict = Body(...)):
    qp = payload.get("payload", {})
    ua = payload.get("user_answer", "")
    ok, msg = tutor.check_answer(qp, ua)
    return {"ok": ok, "message": msg}

# -------------------------------------------------------------------------
# Memory inline router for primary_user (simple, guaranteed mounted)
# -------------------------------------------------------------------------
from fastapi import APIRouter
memory_router = APIRouter(prefix="/memory", tags=["memory"])

@memory_router.get("/primary_user")
def get_primary_user():
    return core.identity.status()

class _PUIn(BaseModel):
    name: str
    alias: Optional[str] = None
    is_admin: bool = True

@memory_router.post("/primary_user")
def set_primary_user(payload: _PUIn):
    ident = core.identity.set_primary_user(payload.name, payload.alias, payload.is_admin)
    return {"ok": True, "primary_user": ident}

app.include_router(memory_router)

# -------------------------------------------------------------------------
# Wake-word background thread
# -------------------------------------------------------------------------
def _wake_thread_loop():
    """
    Calls wait_for_wake_word(core, reya) from your voice/stt.py.
    When wake word detected, speak a randomized reply, then listen for a command,
    transcribe/process it, and respond (optionally speak).
    """
    try:
        while True:
            try:
                # wait_for_wake_word should block until detected (or raise)
                wait_for_wake_word(core, test_mode=False)
                # On wake, speak randomized reply
                reply = random_wake_reply()
                try:
                    speak_with_voice_style(reply, reya)
                except Exception as e:
                    logging.getLogger("uvicorn.error").warning(f"Wake-response TTS failed: {e}")
                # then listen for a command (blocking)
                try:
                    cmd = listen_for_command(core, timeout=10, phrase_time_limit=15, retries=1)
                except Exception as e:
                    logging.getLogger("uvicorn.error").warning(f"listen_for_command error: {e}")
                    cmd = ""
                if cmd:
                    # handle command synchronously (we're in background thread)
                    try:
                        resp = core.handle_text(cmd)
                        # speak response
                        try:
                            speak_with_voice_style(resp, reya)
                        except Exception as e:
                            logging.getLogger("uvicorn.error").warning(f"Wake-response TTS speak failed: {e}")
                    except Exception as e:
                        logging.getLogger("uvicorn.error").exception(f"Error handling command from wake-word: {e}")
                # brief sleep to avoid tight loop
                asyncio.sleep(0.1)
            except Exception as e:
                logging.getLogger("uvicorn.error").warning(f"[WARN] Wake loop exception: {e}")
                # small pause before retrying
                try:
                    time = importlib.import_module("time")
                    time.sleep(0.5)
                except Exception:
                    pass
    except Exception as e:
        logging.getLogger("uvicorn.error").error(f"Wake thread fatal: {e}")

@app.on_event("startup")
def start_background_voice():
    try:
        t = threading.Thread(target=_wake_thread_loop, daemon=True)
        t.start()
        logging.getLogger("uvicorn.error").info("✅ REYA voice background thread launched.")
    except Exception as e:
        logging.getLogger("uvicorn.error").error(f"[ERROR] Could not start voice thread: {e}")

# -------------------------------------------------------------------------
# Diagnostics endpoint convenience
# -------------------------------------------------------------------------
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

# -------------------------------------------------------------------------
# Exported ASGI app (uvicorn will pick this up)
# -------------------------------------------------------------------------
# `app` is already declared above.

# End of file
