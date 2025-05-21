import speech_recognition as sr
from fuzzywuzzy import fuzz
import pyttsx3

recognizer = sr.Recognizer()
mic = sr.Microphone()

# Wake word variants and confidence threshold
WAKE_WORDS = ["reya", "rhea", "raya", "rea"]
MIN_WAKE_CONFIDENCE = 80

# Exit command variants
QUIT_WORDS = ["quit", "exit", "stop", "goodbye"]

# Text-to-speech engine for audible confirmation
tts = pyttsx3.init()
tts.setProperty('rate', 175)  # You can tweak this

def speak(text):
    tts.say(text)
    tts.runAndWait()

def match_wake_word(text):
    """Return True if text is close enough to a wake word."""
    for wake in WAKE_WORDS:
        confidence = fuzz.ratio(wake, text)
        if confidence >= MIN_WAKE_CONFIDENCE:
            print(f"[Wake Check] Heard: {text} (Matched: {wake} @ {confidence}%)")
            return True
    print(f"[Wake Check] Heard: {text} (No match)")
    return False

def wait_for_wake_word(test_mode=False):
    """Listen continuously for a valid wake word."""
    print("🎧 Listening for wake word...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            try:
                audio = recognizer.listen(source)
                text = recognizer.recognize_google(audio).lower()
                if test_mode:
                    print(f"[Test Mode] Heard: {text}")
                if match_wake_word(text):
                    speak("I'm listening.")
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
