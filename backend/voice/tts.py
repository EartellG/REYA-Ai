import pyttsx3

engine = pyttsx3.init()

def speak_with_voice_style(text, reya):
    if not text.strip():
        print("[TTS] Skipped speaking empty text.")
        return

    # Optional: limit to 500 characters
    if len(text) > 500:
        print("[TTS] Response too long, truncating.")
        text = text[:500] + "..."

    # Fix: Unescape text
    cleaned_text = text.encode('utf-8').decode('unicode_escape')

    print(f"🗣️ REYA says: {cleaned_text}")
    try:
        engine.say(cleaned_text)
        engine.runAndWait()
    except KeyboardInterrupt:
        engine.endLoop()


