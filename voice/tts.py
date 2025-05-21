import pyttsx3

engine = pyttsx3.init()

def speak(text):
    if not text.strip():
        print("[TTS] Skipped speaking empty text.")
        return

    # Optional: limit to 300 characters or chunk long text
    if len(text) > 300:
        print("[TTS] Response too long, truncating.")
        text = text[:300] + "..."

    print(f"🗣️ REYA says: {text}")  # Always log spoken response
    try:
        engine.say(text)
        engine.runAndWait()
    except KeyboardInterrupt:
        engine.endLoop()

