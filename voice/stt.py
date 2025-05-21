import speech_recognition as sr
from fuzzywuzzy import fuzz

recognizer = sr.Recognizer()

def match_phrase(heard, target, threshold=80):
    return fuzz.partial_ratio(heard.lower(), target.lower()) >= threshold

def wait_for_wake_word(wake_word="reya"):
    print("🎧 Listening for wake word...")
    while True:
        with sr.Microphone() as source:
            audio = recognizer.listen(source)
        try:
            transcript = recognizer.recognize_google(audio)
            print(f"You said: {transcript}")
            if match_phrase(transcript, wake_word):
                print("👂 Wake word detected!")
                return True
        except sr.UnknownValueError:
            pass  # skip unrecognized speech
        except sr.RequestError:
            print("❌ Speech recognition service error.")

def listen_for_command():
    print("🎤 Listening for your command...")
    with sr.Microphone() as source:
        audio = recognizer.listen(source)
    try:
        command = recognizer.recognize_google(audio)
        print(f"📥 You said: {command}")
        return command
    except sr.UnknownValueError:
        print("😕 I didn't catch that.")
        return ""
    except sr.RequestError:
        print("❌ Speech recognition service error.")
        return ""
