from voice.stt import listen
from voice.tts import speak
from llm_interface import get_response

while True:
    user_input = listen()
    if user_input in ["exit", "quit"]:
        break
    response = get_response(user_input)
    speak(response)