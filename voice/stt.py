import whisper
import speech_recognition as sr

model = whisper.load_model("base")

def listen():
    print("Listening...")
    result = model.transcribe("input.wav")
    return result["text"]



def wait_for_wake_word():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("Waiting for wake word...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio).lower()
            return "reya" in text
        except sr.UnknownValueError:
            return False

def listen():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("Listening...")
        audio = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return ""
