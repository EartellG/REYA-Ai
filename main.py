from voice.stt import listen
from voice.tts import speak
from llm_interface import get_response
from llm_interface import classify_intent
from features import notes, reminders, web_search
from voice.stt import listen
from voice.stt import wait_for_wake_word
from voice.tts import speak
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
    REYA_AI,
    
)


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


