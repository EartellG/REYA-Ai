from voice.edge_tts import speak_with_voice_style
from reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from llm_interface import get_response, get_structured_reasoning_prompt, query_ollama
from features import notes, reminders, web_search
from voice.stt import wait_for_wake_word, listen_for_command
from intent import recognize_intent
from features.language_tutor import LanguageTutor
from utils.translate import translate_to_english
from features.advanced_features import ContextualMemory, ProactiveAssistance, TaskAutomation, EmotionalIntelligence
from features.logic_engine import evaluate_logic
from features.stackoverflow_search import search_stackoverflow
from features.youtube_search import get_youtube_metadata
from features.reddit_search import search_reddit
from features.web_search import search_web

import time

reya = ReyaPersonality(
    traits=[TRAITS["stoic"], TRAITS["playful"]],
    mannerisms=[MANNERISMS["sassy"], MANNERISMS["meta_awareness"]],
    style=STYLES["oracle"],
    voice="en-US-JennyNeural",
    preset={"rate": "-10%", "pitch": "-5Hz", "volume": "+0%"}
)

memory = ContextualMemory()
proactive = ProactiveAssistance(memory)
automation = TaskAutomation()
emotions = EmotionalIntelligence()
tutor = LanguageTutor(memory)

print("🔁 REYA is running...")

def parse_language_level(text):
    # Parse language and level (default to beginner if not specified)
    lang = None
    level = "beginner"

    # Detect language
    if "japanese" in text:
        lang = "Japanese"
    elif "mandarin" in text:
        lang = "Mandarin"

    # Detect level
    if "intermediate" in text:
        level = "intermediate"
    elif "advanced" in text:
        level = "advanced"
    # if no keyword, stays beginner

    return lang, level

while True:
    wait_for_wake_word(reya)
    user_input = listen_for_command(reya)
    print(f"👤 Original input: {user_input}")

    translated_input = translate_to_english(user_input)
    print(f"🌍 Translated to English: {translated_input}")

    if not translated_input:
        continue

    lower_input = translated_input.strip().lower()

    if lower_input in ["quit", "exit", "bye"]:
        speak_with_voice_style("Goodbye!", reya)
        break

    # Language Tutor Start (teach me {language} [level])
    if any(kw in lower_input for kw in ["teach me japanese", "teach me mandarin"]):
        lang, level = parse_language_level(lower_input)
        if lang:
            lesson = tutor.start(language=lang, level=level)
            speak_with_voice_style(lesson, reya)
            memory.remember(f"{lang} {level} lesson", lesson)

            # Track vocab and streak for beginner only (optional: extend to other levels)
            if level == "beginner":
                vocab_map = {
                    "Japanese": ["こんにちは (Hello)", "ありがとう (Thank you)", "さようなら (Goodbye)"],
                    "Mandarin": ["你好 (Nǐ hǎo - Hello)", "谢谢 (Xièxiè - Thank you)", "再见 (Zàijiàn - Goodbye)"]
                }
                if lang in vocab_map:
                    for word in vocab_map[lang]:
                        memory.history.setdefault("language_progress", {}).setdefault(lang, {}).setdefault("vocab_known", []).append(word)
                    memory.history["language_progress"][lang].setdefault("lessons_completed", []).append(level)
                    memory.history["language_progress"][lang]["daily_streak"] = memory.history["language_progress"][lang].get("daily_streak", 0) + 1
                    memory.save()
            continue

    # Language Tutor Quiz (quiz me in {language})
    if any(kw in lower_input for kw in ["quiz me in japanese", "quiz me in mandarin"]):
        lang = "Japanese" if "japanese" in lower_input else "Mandarin"
        quiz_question = tutor.quiz_vocabulary(lang)
        speak_with_voice_style(quiz_question, reya)

        answer = listen_for_command(reya)
        # Basic correctness check for "thank you"
        if "thank" in answer.lower():
            speak_with_voice_style("✅ Correct!", reya)
        else:
            correction = {
                "Japanese": "❌ Not quite. ありがとう means 'Thank you'",
                "Mandarin": "❌ Not quite. 谢谢 means 'Thank you'"
            }
            speak_with_voice_style(correction.get(lang, "❌ Not quite."), reya)
        continue

    # Other features (emotion, intent, automation, logic, web search etc.)
    emotional_response = emotions.analyze_and_respond(translated_input)
    if emotional_response:
        speak_with_voice_style(emotional_response, reya)
        continue

    intent = recognize_intent(translated_input)
    tip = proactive.suggest(translated_input)
    if tip:
        speak_with_voice_style(tip, reya)

    automated = automation.handle(translated_input)
    if automated:
        speak_with_voice_style(automated, reya)
        memory.remember(translated_input, automated)
        continue

    if any(k in translated_input.lower() for k in ["and", "or", "not", "true", "false"]):
        result = evaluate_logic(translated_input)
        speak_with_voice_style(f"The logic result is: {result}", reya)
        continue

    if "stackoverflow" in translated_input.lower() or "code" in translated_input.lower():
        result = search_stackoverflow(translated_input)
        speak_with_voice_style(result, reya)
        memory.remember(translated_input, result)
        continue

    if "youtube" in translated_input.lower():
        metadata = get_youtube_metadata(translated_input)
        if metadata:
            speak_with_voice_style(f"The title is: {metadata.get('title')}", reya)
        else:
            speak_with_voice_style("I couldn't fetch YouTube data.", reya)
        continue

    if "reddit" in translated_input.lower():
        threads = search_reddit(translated_input)
        if threads:
            speak_with_voice_style(f"Here's a Reddit post: {threads[0]}", reya)
        else:
            speak_with_voice_style("No relevant Reddit threads found.", reya)
        continue

    if any(term in translated_input.lower() for term in ["search", "look up"]):
        result = search_web(translated_input)
        speak_with_voice_style(result, reya)
        memory.remember(translated_input, result)
        continue

    # Structured reasoning fallback
    context = memory.get_recent_conversations()
    structured_prompt = get_structured_reasoning_prompt(translated_input, context)
    response = query_ollama(structured_prompt, model="llama3")
    speak_with_voice_style(response, reya)
    memory.remember(user_input, response)

    if response.strip().endswith("?"):
        speak_with_voice_style(f"What would you like me to do next related to '{translated_input}'?", reya)
        follow_up = listen_for_command(reya)
        if follow_up:
            emotional_response = emotions.analyze_and_respond(follow_up)
            if emotional_response:
                speak_with_voice_style(emotional_response, reya)
                continue

            followup_context = memory.get_recent_conversations()
            followup_prompt = get_structured_reasoning_prompt(follow_up, followup_context)
            followup_response = query_ollama(followup_prompt, model="llama3")
            speak_with_voice_style(followup_response, reya)
            memory.remember(follow_up, followup_response)
