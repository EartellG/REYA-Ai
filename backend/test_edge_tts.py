# test_edge_tts.py
import asyncio
from edge_tts import Communicate
from playsound import playsound
import tempfile
import os

async def speak(text):
    communicate = Communicate(text, voice="en-US-JennyNeural", rate="+0%", pitch="+0Hz")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        path = tmp_file.name
    await communicate.save(path)
    print("[Test] Playing:", path)
    playsound(path)
    os.remove(path)

asyncio.run(speak("Hello from edge TTS"))
