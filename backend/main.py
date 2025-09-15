# backend/main.py
from __future__ import annotations
from typing import Optional, Tuple

# --- REYA subsystems (adjust import roots if your modules live elsewhere) ---
from voice.edge_tts import speak_with_voice_style
from reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from llm_interface import get_structured_reasoning_prompt, query_ollama
from features.language_tutor import LanguageTutor
from features.advanced_features import (
    ContextualMemory,
    ProactiveAssistance,
    TaskAutomation,
    EmotionalIntelligence,
)
from features.logic_engine import evaluate_logic
from features.stackoverflow_search import search_stackoverflow
from features.youtube_search import get_youtube_metadata
from features.reddit_search import search_reddit
from features.web_search import search_web
from voice.stt import wait_for_wake_word, listen_for_command
from intent import recognize_intent
from utils.translate import translate_to_english

# --- Personality setup (shared by CLI and API) ---
reya = ReyaPersonality(
    traits=[TRAITS["stoic"], TRAITS["playful"]],
    mannerisms=[MANNERISMS["sassy"], MANNERISMS["meta_awareness"]],
    style=STYLES["oracle"],
    voice="en-GB-MiaNeural",
    preset={"rate": "+12%", "pitch": "-5Hz", "volume": "+0%"},
)

# --- Core re-usable engine ----------------------------------------------------
class ReyaCore:
    """
    Re-usable orchestration of REYA's reasoning pipeline.
    - Stateless entrypoint: handle_text(user_text) -> reply string
    - Internally keeps memory/tutor/etc. so the API and CLI share the same brain.
    """

    def __init__(self):
        self.memory = ContextualMemory()
        self.proactive = ProactiveAssistance(self.memory)
        self.automation = TaskAutomation()
        self.emotions = EmotionalIntelligence()
        self.tutor = LanguageTutor(self.memory)

    # ---------- helper(s)
    @staticmethod
    def _parse_language_level(text: str) -> Tuple[Optional[str], str]:
        t = text.lower()
        lang = None
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

    # ---------- main entrypoint
    def handle_text(self, raw_input: str) -> str:
        """
        Pure text in -> text out. No STT/TTS here.
        Safe to call from FastAPI /chat.
        """
        if not raw_input or not raw_input.strip():
            return ""

        # 1) translate for normalization (still keep original for memory)
        user_input = raw_input.strip()
        translated = translate_to_english(user_input) or user_input
        tlower = translated.lower()

        # 2) quits (for CLI users who pipe here)
        if tlower in {"quit", "exit", "bye"}:
            return "Goodbye!"

        # 3) language tutor start
        if "teach me japanese" in tlower or "teach me mandarin" in tlower:
            lang, level = self._parse_language_level(tlower)
            if lang:
                lesson = self.tutor.start(language=lang, level=level)
                self.memory.remember(f"{lang} {level} lesson", lesson)

                # (optional) track vocab for beginner
                if level == "beginner":
                    vocab_map = {
                        "Japanese": [
                            "こんにちは (Hello)",
                            "ありがとう (Thank you)",
                            "さようなら (Goodbye)",
                        ],
                        "Mandarin": [
                            "你好 (Nǐ hǎo - Hello)",
                            "谢谢 (Xièxiè - Thank you)",
                            "再见 (Zàijiàn - Goodbye)",
                        ],
                    }
                    if lang in vocab_map:
                        hist = self.memory.history.setdefault("language_progress", {})
                        L = hist.setdefault(lang, {})
                        L.setdefault("vocab_known", []).extend(vocab_map[lang])
                        L.setdefault("lessons_completed", []).append(level)
                        L["daily_streak"] = L.get("daily_streak", 0) + 1
                        self.memory.save()
                return lesson

        # 4) language tutor quiz prompt (simple flow)
        if "quiz me in japanese" in tlower or "quiz me in mandarin" in tlower:
            lang = "Japanese" if "japanese" in tlower else "Mandarin"
            return self.tutor.quiz_vocabulary(lang)

        # 5) emotional response
        emo = self.emotions.analyze_and_respond(translated)
        if emo:
            return emo

        # 6) intent + proactive tip (tip is additive; we append)
        intent = recognize_intent(translated)
        tip = self.proactive.suggest(translated)

        # 7) automations (if any returns a terminal response)
        automated = self.automation.handle(translated)
        if automated:
            self.memory.remember(translated, automated)
            return f"{tip + ' ' if tip else ''}{automated}".strip()

        # 8) logic checks (quick path)
        if any(k in tlower for k in [" and ", " or ", " not ", "true", "false"]):
            try:
                result = evaluate_logic(translated)
                return f"{tip + ' ' if tip else ''}The logic result is: {result}"
            finally:
                pass

        # 9) utility lookups
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

        # 10) structured reasoning fallback
        context = self.memory.get_recent_conversations()
        structured_prompt = get_structured_reasoning_prompt(translated, context)
        response = query_ollama(structured_prompt, model="llama3")
        self.memory.remember(user_input, response)

        # Add a proactive next-step if it ended with a question-like answer (UI can decide what to do)
        return f"{response}".strip()


# a single shared core instance you can import in api.py
core = ReyaCore()

# -------------------------- CLI / Voice runner -------------------------------
# backend/main.py  (bottom of file)

def run_assistant():
    # ... your existing while True loop here ...
    pass

if __name__ == "__main__":
    run_assistant()

def run_voice_loop():
    print("🔁 REYA (voice) is running...")
    while True:
        wait_for_wake_word(reya)
        heard = listen_for_command(reya)
        if not heard:
            continue

        print(f"👤 Original input: {heard}")
        reply = core.handle_text(heard)

        if not reply:
            continue

        speak_with_voice_style(reply, reya)
        if reply.strip().lower() == "goodbye!":
            break

        # micro follow-up: if the reply ends with a '?', prompt a follow-up
        if reply.strip().endswith("?"):
            follow = listen_for_command(reya)
            if follow:
                follow_reply = core.handle_text(follow)
                speak_with_voice_style(follow_reply, reya)


if __name__ == "__main__":
    # Keep the voice loop behind the guard so importing this file
    # from FastAPI does NOT start the infinite loop.
    try:
        run_voice_loop()
    except KeyboardInterrupt:
        print("\n👋 Exiting voice loop…")
