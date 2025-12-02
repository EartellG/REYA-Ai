import speech_recognition as sr
from fuzzywuzzy import fuzz
import pyttsx3
import asyncio
import os

from .edge_tts import speak_with_voice_style, _cfg
from dotenv import load_dotenv
from.edge_tts import _cfg

# Force-load .env from project root and backend folder
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)



recognizer = sr.Recognizer()
mic = sr.Microphone()

WAKE_WORDS = ["reya", "rhea", "raya", "rea"]
MIN_WAKE_CONFIDENCE = 80
QUIT_WORDS = ["quit", "exit", "stop", "goodbye"]

# Local pyttsx3 fallback
tts = pyttsx3.init()
tts.setProperty('rate', 175)

def match_wake_word(text: str) -> bool:
    for wake in WAKE_WORDS:
        confidence = fuzz.ratio(wake, text)
        if confidence >= MIN_WAKE_CONFIDENCE:
            print(f"[Wake Check] Heard '{text}' → Matched '{wake}' ({confidence}%)")
            return True
    print(f"[Wake Check] Heard '{text}' → No match")
    return False

def _speak_fallback(text: str):
    """Fallback to local pyttsx3 if Azure/Edge fails."""
    try:
        print(f"[Fallback TTS] Speaking via pyttsx3: {text}")
        tts.say(text)
        tts.runAndWait()
    except Exception as e:
        print(f"[Fallback TTS] Error: {e}")

def wait_for_wake_word(reya, test_mode=False):
    print(f"[DEBUG] Azure key: {bool(_cfg()['AZURE_KEY'])}, Region: {_cfg()['AZURE_REGION']}, Edge Enabled: {_cfg()['EDGE_ENABLED']}")
    print("🎧 Listening for wake word... (say 'Reya')")
    cfg = _cfg()
    azure_ok = bool(cfg["AZURE_KEY"] and cfg["AZURE_REGION"])
    edge_ok = cfg["EDGE_ENABLED"]

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            try:
                audio = recognizer.listen(source)
                text = recognizer.recognize_google(audio).lower()
                if test_mode:
                    print(f"[Test Mode] Heard: {text}")

                if match_wake_word(text):
                    print("✨ Wake word detected! Listening for command...")

                    # Use Azure or Edge if configured
                    try:
                        if azure_ok or edge_ok:
                            speak_with_voice_style("How may I assist you?", reya)
                        else:
                            _speak_fallback("How may I assist you?")
                    except Exception as e:
                        print(f"[WARN] Wake-response TTS failed: {e}")
                        _speak_fallback("How may I assist you?")

                    return  # Continue to command listening
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"[ERROR] Speech Recognition error: {e}")
                continue

def listen_for_command(reya, timeout=10, phrase_time_limit=15, retries=1):
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

        if len(command.split()) < 3 and retries > 0:
            speak_with_voice_style("That was a bit short. Can you repeat it more clearly?", reya)
            return listen_for_command(reya, timeout, phrase_time_limit, retries=retries - 1)

        return command

    except sr.UnknownValueError:
        if retries > 0:
            speak_with_voice_style("I didn't catch that. Could you say it again?", reya)
            return listen_for_command(reya, timeout, phrase_time_limit, retries=retries - 1)
        return "I didn't catch that."

    except sr.RequestError as e:
        return f"Speech Recognition error: {e}"
