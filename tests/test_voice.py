from voice.stt import listen
from voice.tts import speak

print("🎤 Say something after the beep...")
text = listen()
print(f"📝 You said: {text}")
speak(f"You said: {text}")
