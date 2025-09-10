# backend/features/language_tutor.py
import random
from typing import Dict, List, Optional, Tuple, Any, Union, TypedDict

class VocabItem(TypedDict):
    native: str
    translated: str

def _ensure_lang_state(memory, language: str) -> Dict[str, Any]:
    """
    Ensures language progress structure exists in memory.history["language_progress"][language].
    """
    lp = memory.history.setdefault("language_progress", {})
    state = lp.setdefault(language, {
        "vocab_known": [],          # List[VocabItem] (may contain legacy strings)
        "lessons_completed": [],    # List[str]
        "daily_streak": 0,          # int
        "last_level": None,         # str | None
        "last_lesson_id": None,     # str | None
    })
    return state

def _normalize_vocab_list(
    vocab: List[Union[str, Dict[str, Any]]]
) -> List[VocabItem]:
    """
    Accepts ["こんにちは - Hello", ...] or [{"native": "...", "translated": "..."}, ...]
    and returns a uniform list of dicts: [{"native": "...", "translated": "..."}, ...]
    """
    norm: List[VocabItem] = []
    for item in vocab:
        if isinstance(item, dict):
            native = str(item.get("native", "")).strip()
            translated = str(item.get("translated", "")).strip()
            if native and translated:
                norm.append({"native": native, "translated": translated})
        else:
            parts = [p.strip() for p in str(item).split(" - ", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                norm.append({"native": parts[0], "translated": parts[1]})
    return norm

def _merge_vocab(memory, language: str, new_items: List[VocabItem]) -> None:
    """
    Merge normalized vocab items into memory without duplicates.
    """
    state = _ensure_lang_state(memory, language)

    # Existing may be a mix of strings and dicts (legacy). Normalize first.
    existing_raw: List[Union[str, Dict[str, Any]]] = (
        state.get("vocab_known") or memory.get_vocab(language) or []
    )
    existing: List[VocabItem] = _normalize_vocab_list(existing_raw)

    # De-dupe by (native, translated)
    seen = {(e["native"], e["translated"]) for e in existing}
    for n in new_items:
        key = (n["native"], n["translated"])
        if key not in seen:
            existing.append(n)
            seen.add(key)

    state["vocab_known"] = existing
    memory.save()

def _lesson(language: str, level: str) -> Tuple[str, List[VocabItem], str, str]:
    """
    Returns: (lesson_id, vocab_items, grammar_tip, title)
    """
    if language == "Japanese":
        if level == "beginner":
            lesson_id = "jp_beginner_1"
            vocab = _normalize_vocab_list([
                "こんにちは - Hello", "ありがとう - Thank you", "さようなら - Goodbye"
            ])
            grammar = "Basic SOV order. Ex: 私はりんごを食べます。"
            title = "JP Beginner — Greetings"
        elif level == "intermediate":
            lesson_id = "jp_intermediate_1"
            vocab = _normalize_vocab_list([
                "勉強する - To study", "図書館 - Library", "宿題 - Homework"
            ])
            grammar = "Use ～ている for ongoing actions: 勉強しています = is studying."
            title = "JP Intermediate — Study & School"
        elif level == "advanced":
            lesson_id = "jp_advanced_1"
            vocab = _normalize_vocab_list([
                "仮定 - Hypothesis", "逆説 - Paradox", "抽象的 - Abstract"
            ])
            grammar = "Connectors: にもかかわらず (despite), ながらも (although)."
            title = "JP Advanced — Academic terms"
        else:
            raise ValueError(f"Unknown level: {level}")

    elif language == "Mandarin":
        if level == "beginner":
            lesson_id = "zh_beginner_1"
            vocab = _normalize_vocab_list([
                "你好 - Hello", "谢谢 - Thank you", "再见 - Goodbye"
            ])
            grammar = "Mandarin has four tones: 妈(mā) 麻(má) 马(mǎ) 骂(mà)."
            title = "ZH Beginner — Greetings"
        elif level == "intermediate":
            lesson_id = "zh_intermediate_1"
            vocab = _normalize_vocab_list([
                "图书馆 - Library", "学习 - Study", "作业 - Homework"
            ])
            grammar = "SVO order. 他在图书馆学习。 (He studies in the library.)"
            title = "ZH Intermediate — Study & School"
        elif level == "advanced":
            lesson_id = "zh_advanced_1"
            vocab = _normalize_vocab_list([
                "抽象 - Abstract", "假设 - Hypothesis", "悖论 - Paradox"
            ])
            grammar = "Patterns: 虽然…但是… / 尽管…还是…"
            title = "ZH Advanced — Academic terms"
        else:
            raise ValueError(f"Unknown level: {level}")
    else:
        raise ValueError(f"Unsupported language: {language}")

    return lesson_id, vocab, grammar, title

class LanguageTutor:
    def __init__(self, memory):
        self.memory = memory

    # ---------- core API ----------
    def start(
        self,
        language: str = "Japanese",
        level: str = "beginner",
        *,
        resume: bool = False
    ) -> str:
        state = _ensure_lang_state(self.memory, language)

        if resume and state.get("last_level") and state.get("last_lesson_id"):
            return self.resume(language)

        try:
            lesson_id, vocab_items, grammar, title = _lesson(language, level)
        except ValueError as e:
            return str(e)

        _merge_vocab(self.memory, language, vocab_items)

        self.memory.mark_lesson_completed(language, lesson_id)
        self.memory.increment_streak(language)

        state["last_level"] = level
        state["last_lesson_id"] = lesson_id
        self.memory.save()

        words_list = ", ".join(f"{v['native']} - {v['translated']}" for v in vocab_items)
        return (
            f"Starting {language} ({level}) — {title}\n"
            f"Today's words: {words_list}\n"
            f"Grammar tip: {grammar}\n"
            f"(Progress saved. Streak: {self.memory.get_streak(language)})"
        )

    def resume(self, language: str) -> str:
        state = _ensure_lang_state(self.memory, language)
        level = state.get("last_level")
        lesson_id = state.get("last_lesson_id")
        if not (level and lesson_id):
            return f"No saved progress in {language} yet. Try starting a {language} lesson."
        return f"Resuming {language}: last level **{level}**, lesson **{lesson_id}**. Ready when you are!"

    def next_lesson(self, language: str) -> str:
        state = _ensure_lang_state(self.memory, language)
        last = state.get("last_lesson_id")
        if not last:
            return f"No lessons completed in {language} yet. Start with beginner?"

        if "beginner" in last:
            level = "intermediate"
        elif "intermediate" in last:
            level = "advanced"
        else:
            return f"You’re at the highest level in {language} for the current curriculum."

        return self.start(language, level)

    # ---------- quizzing ----------
    def quiz_vocabulary(self, language: str) -> Optional[Dict[str, Any]]:
        """
        Returns a quiz payload or None if no vocab yet.
        {
          "question": "What does 'こんにちは' mean?",
          "answer": "Hello",
          "native": "こんにちは",
          "options": ["Hello", "Goodbye", "Thank you", "Excuse me"]
        }
        """
        state = _ensure_lang_state(self.memory, language)
        vocab_raw = state.get("vocab_known") or self.memory.get_vocab(language) or []
        vocab: List[VocabItem] = _normalize_vocab_list(vocab_raw)

        if not vocab:
            return None

        correct = random.choice(vocab)
        distractors = [v for v in vocab if v is not correct]
        random.shuffle(distractors)
        choices = [correct["translated"]] + [d["translated"] for d in distractors[:3]]
        random.shuffle(choices)

        return {
            "question": f"What does '{correct['native']}' mean?",
            "answer": correct["translated"],
            "native": correct["native"],
            "options": choices,
        }

    def check_answer(self, quiz_payload: Dict[str, Any], user_answer: str) -> Tuple[bool, str]:
        correct = (quiz_payload.get("answer") or "").strip()
        ok = (user_answer or "").strip().lower() == correct.lower()
        return ok, ("Correct! 🎉" if ok else f"Not quite. The answer is '{correct}'.")

    # ---------- info / utilities ----------
    def get_progress(self, language: str) -> Dict[str, Any]:
        state = _ensure_lang_state(self.memory, language)
        lessons = state.get("lessons_completed", [])
        vocab_raw = state.get("vocab_known") or self.memory.get_vocab(language) or []
        vocab: List[VocabItem] = _normalize_vocab_list(vocab_raw)

        return {
            "language": language,
            "streak": self.memory.get_streak(language),
            "last_level": state.get("last_level"),
            "last_lesson_id": state.get("last_lesson_id"),
            "lessons_completed": lessons,
            "vocab_count": len(vocab),
            "sample_vocab": vocab[:8],
        }

    def add_custom_vocab(self, language: str, items: List[Dict[str, str]]) -> str:
        """
        items: [{"native": "...", "translated": "..."}, ...]
        """
        # items already dicts, but run through normalizer for safety
        norm = _normalize_vocab_list(items)  # type: ignore[arg-type]
        _merge_vocab(self.memory, language, norm)
        return f"Added {len(norm)} custom vocab items to {language}."
