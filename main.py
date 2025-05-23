from voice.edge_tts import speak_with_voice_style
from reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES
from llm_interface import get_response, get_structured_reasoning_prompt, query_ollama
from features import notes, reminders, web_search
from voice.stt import wait_for_wake_word, listen_for_command
from intent import recognize_intent
from features.language_tutor import LanguageTutor
from utils.translate import translate_to_english
from features.advanced_features import (
    ContextualMemory,
    ProactiveAssistance,
    TaskAutomation,
    EmotionalIntelligence
)
from features.logic_engine import evaluate_logic
from features.stackoverflow_search import search_stackoverflow
from features.youtube_search import get_youtube_metadata
from features.reddit_search import search_reddit
from features.web_search import search_web


def main():
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

    while True:
        wait_for_wake_word(reya)
        user_input = listen_for_command(reya)
        print(f"👤 Original input: {user_input}")

        translated_input = translate_to_english(user_input)
        print(f"🌍 Translated to English: {translated_input}")
        if not translated_input:
            continue

        if translated_input.strip().lower() in ["quit", "exit", "bye"]:
            speak_with_voice_style("Goodbye!", reya)
            break

        # Language Tutor: Japanese
        if "teach me japanese" in translated_input.lower():
            memory.history.setdefault("language_progress", {})
            memory.history["language_progress"].setdefault("Japanese", {
                "vocab_known": [], "lessons_completed": [], "daily_streak": 0
            })
            lesson = tutor.start(language="Japanese", level="beginner")
            speak_with_voice_style(lesson, reya)
            memory.remember("Japanese lesson", lesson)

            vocab = ["こんにちは (Hello)", "ありがとう (Thank you)", "さようなら (Goodbye)"]
            memory.history["language_progress"]["Japanese"]["vocab_known"].extend(vocab)
            memory.history["language_progress"]["Japanese"]["lessons_completed"].append("beginner")
            memory.history["language_progress"]["Japanese"]["daily_streak"] += 1
            memory.save()
            continue


        if "quiz me in japanese" in translated_input.lower():
            quiz = tutor.quiz_vocabulary("Japanese")
            speak_with_voice_style(quiz, reya)
            answer = listen_for_command(reya)
            if any(kw in answer.lower() for kw in ["ありがとう", "thank you"]):
                speak_with_voice_style("✅ Correct!", reya)
            else:
                speak_with_voice_style("❌ Not quite. ありがとう means 'Thank you'", reya)
            continue

        # Language Tutor: Mandarin
        if "teach me mandarin" in translated_input.lower():
            memory.history.setdefault("language_progress", {})
            memory.history["language_progress"].setdefault("Mandarin", {
                "vocab_known": [], "lessons_completed": [], "daily_streak": 0
            })
            lesson = tutor.start(language="Mandarin", level="beginner")
            speak_with_voice_style(lesson, reya)
            memory.remember("Mandarin lesson", lesson)

            vocab = ["你好 (Hello)", "谢谢 (Thank you)", "再见 (Goodbye)"]
            memory.history["language_progress"]["Mandarin"]["vocab_known"].extend(vocab)
            memory.history["language_progress"]["Mandarin"]["lessons_completed"].append("beginner")
            memory.history["language_progress"]["Mandarin"]["daily_streak"] += 1
            memory.save()
            continue

        if "quiz me in mandarin" in translated_input.lower():
            quiz = tutor.quiz_vocabulary("Mandarin")
            speak_with_voice_style(quiz, reya)
            answer = listen_for_command(reya)
            if any(kw in answer.lower() for kw in ["谢谢", "thank you"]):
                speak_with_voice_style("✅ Correct!", reya)
            else:
                speak_with_voice_style("❌ Not quite. 谢谢 means 'Thank you'", reya)
            continue

        # Emotions
        emotional_response = emotions.analyze_and_respond(translated_input)
        if emotional_response:
            speak_with_voice_style(emotional_response, reya)
            continue

        # Proactive Tips
        intent = recognize_intent(translated_input)
        tip = proactive.suggest(translated_input)
        if tip:
            speak_with_voice_style(tip, reya)

        # Automation
        automated = automation.handle(translated_input)
        if automated:
            speak_with_voice_style(automated, reya)
            memory.remember(translated_input, automated)
            continue

        # Logic
        if any(k in translated_input.lower() for k in ["and", "or", "not", "true", "false"]):
            result = evaluate_logic(translated_input)
            speak_with_voice_style(f"The logic result is: {result}", reya)
            continue

        # StackOverflow
        if "stackoverflow" in translated_input.lower() or "code" in translated_input.lower():
            result = search_stackoverflow(translated_input)
            speak_with_voice_style(result, reya)
            memory.remember(translated_input, result)
            continue

        # YouTube
        if "youtube" in translated_input.lower():
            metadata = get_youtube_metadata(translated_input)
            if metadata:
                speak_with_voice_style(f"The title is: {metadata.get('title')}", reya)
            else:
                speak_with_voice_style("I couldn't fetch YouTube data.", reya)
            continue

        # Reddit
        if "reddit" in translated_input.lower():
            threads = search_reddit(translated_input)
            if threads:
                speak_with_voice_style(f"Here's a Reddit post: {threads[0]}", reya)
            else:
                speak_with_voice_style("No relevant Reddit threads found.", reya)
            continue

        # Web Search
        if any(term in translated_input.lower() for term in ["search", "look up"]):
            result = search_web(translated_input)
            speak_with_voice_style(result, reya)
            memory.remember(translated_input, result)
            continue

        # Structured Reasoning
        context = memory.get_recent_conversations()
        structured_prompt = get_structured_reasoning_prompt(translated_input, context)
        response = query_ollama(structured_prompt, model="llama3")
        speak_with_voice_style(response, reya)
        memory.remember(user_input, response)

        if response.strip().endswith("?"):
            speak_with_voice_style(f"What would you like me to do next related to '{translated_input}'?", reya)
            print("🕒 Listening for follow-up...")
            follow_up = listen_for_command(reya)
            print(f"🔁 Follow-up: {follow_up}")

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


if __name__ == "__main__":
    main()
