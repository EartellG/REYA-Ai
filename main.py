from voice.tts import speak
from llm_interface import get_response, get_structured_reasoning_prompt, classify_intent, query_ollama
from features import notes, reminders, web_search
from voice.stt import wait_for_wake_word, listen_for_command
from intent import recognize_intent
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

memory = ContextualMemory()
proactive = ProactiveAssistance(memory)
automation = TaskAutomation()
emotions = EmotionalIntelligence()


print("🔁 REYA is running...")

while True:
    wait_for_wake_word()
    user_input = listen_for_command()
    print(f"👤 You said: {user_input}")

    emotional_response = emotions.analyze_and_respond(user_input)

    if not user_input:
        continue

    # Goodbye logic
    if user_input.strip().lower() in ["quit", "exit", "bye"]:
        speak("Goodbye!")
        break

    # Emotion detection
    emotional_response = emotions.analyze_and_respond(user_input)
    if emotional_response:
        speak(emotional_response)
        continue

    # Proactive tip
    tip = proactive.suggest(user_input)
    if tip:
        speak(tip)

    # Task automation
    automated = automation.handle(user_input)
    if automated:
        speak(automated)
        memory.remember(user_input, automated)
        continue

    # Logic evaluation
    if any(k in user_input.lower() for k in ["and", "or", "not", "true", "false"]):
        result = evaluate_logic(user_input)
        speak(f"The logic result is: {result}")
        continue

    # StackOverflow
    if "stackoverflow" in user_input.lower() or "code" in user_input.lower():
        result = search_stackoverflow(user_input)
        speak(result)
        memory.remember(user_input, result)
        continue

    # YouTube
    if "youtube" in user_input.lower():
        metadata = get_youtube_metadata(user_input)
        if metadata:
            speak(f"The title is: {metadata.get('title')}")
        else:
            speak("I couldn't fetch YouTube data.")
        continue

    # Reddit
    if "reddit" in user_input.lower():
        threads = search_reddit(user_input)
        if threads:
            speak(f"Here's a Reddit post: {threads[0]}")
        else:
            speak("No relevant Reddit threads found.")
        continue

    # Web Search
    if any(term in user_input.lower() for term in ["search", "look up"]):
        result = search_web(user_input)
        speak(result)
        memory.remember(user_input, result)
        continue

    # General LLM reasoning
    context = memory.get_recent_conversations()
    structured_prompt = get_structured_reasoning_prompt(user_input, context)
    response = query_ollama(structured_prompt, model="llama3")
    speak(response)
    memory.remember(user_input, response)

    # Optional follow-up
    speak(f"What would you like me to do next related to '{user_input}'?")
