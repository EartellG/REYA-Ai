from __future__ import annotations
from typing import Optional, Tuple, cast

# ===================== REYA Core & Utilities =====================
from .voice.edge_tts import speak_with_voice_style, engine_status
from .reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from .llm_interface import get_structured_reasoning_prompt, query_ollama
from .features.language_tutor import LanguageTutor
from .features.advanced_features import (
    ContextualMemory,
    ProactiveAssistance,
    TaskAutomation,
    EmotionalIntelligence,
)
from .features.logic_engine import evaluate_logic
from .features.stackoverflow_search import search_stackoverflow
from .features.youtube_search import get_youtube_metadata
from .features.reddit_search import search_reddit
from .features.web_search import search_web
from .voice.stt import wait_for_wake_word, listen_for_command
from .intent import recognize_intent
from .utils.translate import translate_to_english
from .utils.sanitize import sanitize_response
from .features.identity import IdentityStore


# ===================== Personality =====================
reya = ReyaPersonality(
    traits=[TRAITS["stoic"], TRAITS["playful"]],
    mannerisms=[MANNERISMS["sassy"], MANNERISMS["meta_awareness"]],
    style=STYLES["oracle"],
    voice="en-GB-SoniaNeural",
    preset={"rate": "+12%", "pitch": "-5Hz", "volume": "+0%"},
)


# ===================== Core Brain =====================
class ReyaCore:
    def __init__(self):
        self.memory = ContextualMemory()
        self.proactive = ProactiveAssistance(self.memory)
        self.automation = TaskAutomation()
        self.emotions = EmotionalIntelligence()
        self.tutor = LanguageTutor(self.memory)
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

        if "who am i" in tlower or "who are you" in tlower:
            pu = self.identity.get_primary_user()
            me = "Reya"
            you = (pu.get("alias") or pu.get("name")) if pu else "friend"
            return sanitize_response(f"I am {me}. You are {you}.")

        if tlower in {"quit", "exit", "bye"}:
            return "Goodbye!"

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

        if any(k in tlower for k in [" and ", " or ", " not ", "true", "false"]):
            try:
                result = evaluate_logic(translated)
                return f"{tip + ' ' if tip else ''}The logic result is: {result}"
            finally:
                pass

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

        context = self.memory.get_recent_conversations()
        structured_prompt = get_structured_reasoning_prompt(translated, context)
        response = query_ollama(structured_prompt, model="llama3")
        self.memory.remember(user_input, response)
        return sanitize_response(f"{response}".strip())


core = ReyaCore()


# ===================== FastAPI App =====================
import os
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Core backend routes
from .routes.workspace import router as workspace_router
from .routes.roles_reviewer import router as reviewer_router
from .routes.roles_fixer import router as fixer_router
from backend.api import (
    reya,
    settings_router,
    voice_router,
    tts_router,
    roles_coder_router,
    roles_reviewer_router,
    roles_fixer_router,
    roles_monetizer_router,
    workspace_router as api_workspace_router,
)

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


def create_app() -> FastAPI:
    app = FastAPI(title="REYA Backend", version="3.4")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_workspace_router)
    app.include_router(reviewer_router)
    app.include_router(fixer_router)
    app.include_router(settings_router)
    app.include_router(voice_router)
    app.include_router(tts_router)
    app.include_router(roles_coder_router)
    app.include_router(roles_reviewer_router)
    app.include_router(roles_fixer_router)
    app.include_router(roles_monetizer_router)
    app.include_router(memory_router)

    print(f"[REYA] 🔊 TTS Engine Status → {engine_status()}")

    @app.get("/_debug/routes")
    def _debug_routes():
        return sorted([f"{r.path}" for r in app.router.routes])

    @app.get("/")
    def root():
        return {
            "ok": True,
            "service": "reya-backend",
            "version": "3.4",
            "tts_engine": engine_status().get("engine_choice"),
            "primary_user": core.identity.preferred_display_name(),
        }

    return app


app = create_app()


# ======================================================
# 🗣️ Launch Wake Word + API Together
# ======================================================
import threading


def background_voice_loop():
    """Run the wake-word listener in a separate thread."""
    try:
        print("🎤 REYA wake-word detection starting...")
        wait_for_wake_word(core, reya)
    except Exception as e:
        print(f"[WARN] Wake-word loop stopped: {e}")


@app.on_event("startup")
def start_background_voice():
    try:
        thread = threading.Thread(target=background_voice_loop, daemon=True)
        thread.start()
        print("✅ REYA voice background thread launched.")
    except Exception as e:
        print(f"[ERROR] Could not start voice thread: {e}")
