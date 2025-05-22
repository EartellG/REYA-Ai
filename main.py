from voice.tts import speak
from llm_interface import get_response, get_structured_reasoning_prompt, classify_intent, query_ollama
from features import notes, reminders, web_search
from voice.stt import wait_for_wake_word, listen_for_command
from intent import recognize_intent
from features.advanced_features import (
    ContextualMemory, ProactiveAssistance, TaskAutomation, EmotionalIntelligence,
    PersonalizedKnowledgeBase, SmartDeviceIntegration, PrivacyControls,
    VoiceInterface, MultiModalProcessor
)
from features.logic_engine import evaluate_logic
from features.stackoverflow_search import search_stackoverflow
from features.youtube_search import get_youtube_metadata
from features.reddit_search import search_reddit

# Initialize systems
memory = ContextualMemory()
proactive = ProactiveAssistance(memory)
automation = TaskAutomation()
emotions = EmotionalIntelligence()
knowledge = PersonalizedKnowledgeBase()
devices = SmartDeviceIntegration()
privacy = PrivacyControls()
voice = VoiceInterface()
multimodal = MultiModalProcessor()

print("\U0001F501 REYA is running...")

while True:
    wait_for_wake_word()
    user_input = listen_for_command()
    if not user_input:
        continue

    print(f"\U0001F464 You said: {user_input}")

    if user_input.lower().strip() in ["quit", "exit", "bye"]:
        speak("Goodbye.")
        break

    # Logic engine
    if any(op in user_input.lower() for op in ["and", "or", "not", "true", "false"]):
        result = evaluate_logic(user_input)
        speak(f"The logic result is: {result}")
        continue

    # StackOverflow
    if "code" in user_input or "stackoverflow" in user_input:
        result = search_stackoverflow(user_input)
        speak(f"Here's a StackOverflow result: {result}")
        memory.remember(user_input, result)
        continue

    # YouTube
    if "youtube" in user_input:
        metadata = get_youtube_metadata(user_input)
        if metadata:
            speak(f"The title is: {metadata.get('title')}")
        else:
            speak("I couldn't fetch data from YouTube.")
        continue

    # Reddit
    if "reddit" in user_input:
        threads = search_reddit(user_input)
        if threads:
            speak(f"Here's a Reddit post: {threads[0]}")
        else:
            speak("No relevant Reddit threads found.")
        continue

    # Search intent
    if "search" in user_input.lower() or "look up" in user_input.lower():
        result = search_web(user_input)
        speak(result)
        memory.remember(user_input, result)
        continue

    # General conversation
    context = memory.recall().get("conversations", [])
    structured_prompt = get_structured_reasoning_prompt(user_input, context)
    response = query_ollama(structured_prompt, model="llama3")

    # Handle long responses
    if len(response.split()) > 50:
        short_response = response.split(". ")[0] + "."
        speak(short_response)
        speak("Would you like more details?")
        follow_up = listen_for_command()
        if follow_up.lower() in ["yes", "sure", "go ahead"]:
            speak(response)
    else:
        speak(response)

    memory.remember(user_input, response)
