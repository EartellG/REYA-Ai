from voice.stt import listen
from voice.tts import speak
from llm_interface import get_response
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