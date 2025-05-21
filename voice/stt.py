import speech_recognition as sr
from fuzzywuzzy import fuzz

recognizer = sr.Recognizer()
mic = sr.Microphone()

WAKE_WORD = "reya"
QUIT_WORDS = ["quit", "exit", "stop", "goodbye"]

def wait_for_wake_word():
    print("🎧 Listening for wake word...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            try:
                audio = recognizer.listen(source)
                text = recognizer.recognize_google(audio).lower()
                print(f"[Wake Check] Heard: {text}")
                if fuzz.ratio(WAKE_WORD, text) > 80:
                    return
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"[ERROR] Speech Recognition error: {e}")
                continue

def listen_for_command():
    print("🎤 Listening for command...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"[Command] {command}")
        return command
    except sr.UnknownValueError:
        return "I didn't catch that."
    except sr.RequestError as e:
        return f"Speech Recognition error: {e}"
