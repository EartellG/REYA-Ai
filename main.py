from voice.tts import speak
from llm_interface import get_response
from llm_interface import classify_intent
from features import notes, reminders, web_search
from voice.stt import wait_for_wake_word, listen_for_command
from intent import recognize_intent
from features.stackoverflow_search import search_stackoverflow
from features.youtube_search import get_youtube_metadata
from features.reddit_search import search_reddit
from features.web_search import search_web
from voice.stt import listen_for_command
from memory import memory
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

memory = ContextualMemory(memory_file="path/to/memory/file.json")
proactive = ProactiveAssistance(memory)
automation = TaskAutomation()
emotions = EmotionalIntelligence()
knowledge = PersonalizedKnowledgeBase()
devices = SmartDeviceIntegration()
privacy = PrivacyControls()
voice = VoiceInterface()
multimodal = MultiModalProcessor()

# After generating a response:
memory.remember(user_input, response)

print("🔁 REYA is running...")

while True:
    wait_for_wake_word()  # 👂 Wait for "Reya"
    speak("I'm listening.")
    print("🎧 Listening for your command...")

    user_input = listen_for_command()
    print("You said:", user_input)

    intent = recognize_intent(user_input)

    if intent == "exit":
        speak("Goodbye!")
        break

    elif intent == "greeting":
        speak("Hello! How can I assist you today?")

    elif intent == "stackoverflow_help":
        result = search_stackoverflow(user_input)
        print(result)
        speak(result)

    elif intent == "youtube_info":
        result = get_youtube_metadata(user_input)
        print(result)
        speak(result)

    elif intent == "reddit_search":
        result = search_reddit(user_input)
        print(result)
        speak(result)

    elif intent == "web_search":
        result = search_web(user_input)
        print(result)
        speak(result)

    else:
        result = get_response(user_input)
        print(result)
        speak(result)



while True:
    user_input = listen()
    if user_input in ["exit", "quit","thanks","thank you"]:
        break
    response = get_response(user_input)
    speak(response)

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
    ...

    follow_up = "Do you want me to explain how I got that?" if "why" in user_input.lower() else None
    if follow_up:
     speak(follow_up)


