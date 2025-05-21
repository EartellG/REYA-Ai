from voice.tts import speak
from llm_interface import get_response, get_structured_reasoning_prompt
from llm_interface import classify_intent
from features import notes, reminders, web_search
from voice.stt import wait_for_wake_word, listen_for_command
from intent import recognize_intent
from features.advanced_features import ContextualMemory
from features.logic_engine import evaluate_logic
from features.stackoverflow_search import search_stackoverflow
from features.youtube_search import get_youtube_metadata
from features.reddit_search import search_reddit
from features.web_search import search_web
from voice.stt import listen_for_command
from features.advanced_features import (
      ContextualMemory, 
      ProactiveAssistance,
      TaskAutomation,
      EmotionalIntelligence,
      PersonalizedKnowledgeBase,
      SmartDeviceIntegration,
      PrivacyControls,
      VoiceInterface,
      MultiModalProcessor,
)

memory = ContextualMemory()
proactive = ProactiveAssistance(memory)
automation = TaskAutomation()
emotions = EmotionalIntelligence()
knowledge = PersonalizedKnowledgeBase()
devices = SmartDeviceIntegration()
privacy = PrivacyControls()
voice = VoiceInterface()
multimodal = MultiModalProcessor()
intent = recognize_intent("some_command")



import time

print("🔁 REYA is running...")

while True:
    wait_for_wake_word()  # 👂 Listen for "Reya"
    speak("I'm listening.")  # Optional response to confirm wake

    user_input = listen_for_command()
    print(f"👤 You said: {user_input}")

    # --- Handle exit ---
    if user_input.lower() in ["quit", "exit", "stop", "goodbye"]:
        speak("Goodbye.")
        break

    # --- Logic engine trigger ---
    if any(keyword in user_input.lower() for keyword in ["and", "or", "not", "true", "false"]):
        result = evaluate_expression(user_input)
        speak(f"The logical result is: {result}")
        continue

    # --- Web search trigger ---
    if "search" in user_input.lower() or "look up" in user_input.lower():
        search_result = search_web(user_input)
        speak(search_result)
        memory.remember(user_input, search_result)
        continue

    # --- General LLM reasoning ---
    context = memory.get_recent_conversations()
    response = get_response(user_input, context)
    speak(response)
    memory.add_conversation(user_input, response)

# Structured prompt with context
context = memory.recall()
structured_prompt = get_structured_reasoning_prompt(user_input, context)
response = get_response(structured_prompt)

speak(response)
memory.remember(user_input, response)

# Optionally: Let REYA ask a question back
follow_up = f"What would you like me to do next related to '{user_input}'?"
speak(follow_up)


while True:
    user_input = listen_for_command()
    if user_input in ["exit", "quit","thanks","thank you"]:
        break
    response = get_response(user_input)
    speak(response)

    # After generating a response:
memory.remember(user_input, response)

while True:
    user_input = listen_for_command()
    if not user_input:
        continue

    print(f"👤 You said: {user_input}")

    if any(quit_word in user_input.lower() for quit_word in QUIT_WORDS):
        speak("Goodbye.")
        break

    # 🔢 Logic evaluation if input contains logic keywords
    elif "and" in user_input or "or" in user_input or "not" in user_input:
        result = evaluate_logic(user_input)
        speak(f"The logic result is: {result}")

    # 🔍 StackOverflow if coding help
    elif "code" in user_input or "stackoverflow" in user_input:
        results = search_stackoverflow(user_input)
        speak(f"Here's a StackOverflow result: {results}")

    # 📺 YouTube metadata
    elif "youtube" in user_input:
        metadata = get_youtube_metadata(user_input)
        if metadata:
            speak(f"The title is: {metadata.get('title')}")
        else:
            speak("I couldn't fetch data from YouTube.")

    # 👥 Reddit
    elif "reddit" in user_input:
        threads = search_reddit(user_input)
        if threads:
            speak(f"Here's a Reddit post: {threads[0]}")
        else:
            speak("No relevant Reddit threads found.")

    # 🤖 Otherwise, default to LLM
    else:
        context = memory.recall()
        prompt = get_structured_reasoning_prompt(user_input, context)
        response = get_response(prompt)
        speak(response)
        memory.add(user_input, response)


while True:
     user_input = listen()
     if not user_input:
        continue

     intent = classify_intent(user_input)

     if intent == "note":
        response = notes.handle(user_input)
     elif intent == "reminder":
        response = reminders.handle(user_input)
     elif intent == "web_search":
        response = web_search.search(user_input)
     elif intent == "greeting":
        response = "Hello! How can I help you today?"
     elif intent == "exit":
        response = "Goodbye!"
        speak(response)
        break
     else:
      response = "I'm not sure how to help with that yet."
speak(response)

while True:
    if not wait_for_wake_word():
        continue
    user_input = listen()

    



