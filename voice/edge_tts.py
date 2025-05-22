import asyncio
import edge_tts

VOICE = "en-US-JennyNeural"  # You can try others too

async def speak_async(text):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.run()

def speak(text):
    asyncio.run(speak_async(text))
