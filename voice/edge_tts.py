import edge_tts
import asyncio
import uuid
import os
from playsound import playsound

# Voice map based on style
STYLE_VOICE_MAP = {
    "zen": "en-US-AriaNeural",
    "cyberpunk": "en-US-DavisNeural",
    "oracle": "en-US-GuyNeural",
    "teacher": "en-US-JennyNeural",
    "griot": "en-NG-AbeoNeural",
    "detective": "en-US-ChristopherNeural",
    "bard": "en-GB-RyanNeural",
    "companion": "en-US-AnaNeural",
    "default": "en-US-JennyNeural",
}

def get_voice_by_personality(personality):
    return STYLE_VOICE_MAP.get(personality.style, "en-US-JennyNeural")

def get_speech_params(personality):
    voice = get_voice_by_personality(personality)
    rate = "+0%"  # Neutral rate
    pitch = "+0Hz"  # Neutral pitch

    if personality.style == "zen":
        rate = "-15%"
        pitch = "-5Hz"
    elif personality.style == "cyberpunk":
        rate = "+15%"
        pitch = "+10Hz"
    elif personality.style == "oracle":
        rate = "-10%"
        pitch = "-10Hz"

    return voice, rate, pitch

async def speak_with_voice_style_async(text, reya):
    voice = getattr(reya, "voice", "en-US-JennyNeural")
    preset = getattr(reya, "preset", {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"})


    # Create a unique temporary filename
    file_name = f"temp_{uuid.uuid4().hex}.mp3"

    communicate = edge_tts.Communicate(
        text,
        voice=voice,
        rate=preset.get("rate", "+0%"),
        volume=preset.get("volume", "+0%"),
        pitch=preset.get("pitch", "+0Hz"),
    )

    await communicate.save(file_name)
    playsound(file_name)
    os.remove(file_name)

def speak_with_voice_style(text, reya):
    asyncio.run(speak_with_voice_style_async(text, reya))