import speech_recognition as sr
from fuzzywuzzy import fuzz
import pyttsx3
from voice.edge_tts import speak_with_voice_style


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


def match_wake_word(text):
    """Return True if text is close enough to a wake word."""
    for wake in WAKE_WORDS:
        confidence = fuzz.ratio(wake, text)
        if confidence >= MIN_WAKE_CONFIDENCE:
            print(f"[Wake Check] Heard: {text} (Matched: {wake} @ {confidence}%)")
            return True
    print(f"[Wake Check] Heard: {text} (No match)")
    return False

def wait_for_wake_word(reya, test_mode=False):
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
                    speak_with_voice_style("How may I assist you?", reya)
                    return
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"[ERROR] Speech Recognition error: {e}")
                continue

def listen_for_command(reya,timeout=10, phrase_time_limit=15, retries=1):
    print("🎤 Listening for command...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            print("⏱️ Timeout: No speech detected.")
            return "I didn't hear anything."

    try:
        command = recognizer.recognize_google(audio).lower()
        print(f"[Command] {command}")

        # Retry if too short or unclear
        if len(command.split()) < 3 and retries > 0:
            speak_with_voice_style("That was a bit short. Can you repeat it more clearly?", reya)
            return listen_for_command (reya, timeout, phrase_time_limit, retries=retries - 1)

        return command

    except sr.UnknownValueError:
        if retries > 0:
            speak_with_voice_style("I didn't catch that. Could you say it again?", reya)
            return listen_for_command(reya, timeout, phrase_time_limit, retries=retries - 1)
        return "I didn't catch that."

    except sr.RequestError as e:
        return f"Speech Recognition error: {e}"
