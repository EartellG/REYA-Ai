import edge_tts
import asyncio
import tempfile
import os
from pydub import AudioSegment
from pydub.playback import play


def get_voice_and_preset(reya):
    """
    Extracts voice name and style preset from REYA's personality.
    """
    style_to_voice = {
        "oracle": "en-US-JennyNeural",
        "griot": "en-US-GuyNeural",
        "cyberpunk": "en-US-DavisNeural",
        "zen": "en-US-AriaNeural",
        "detective": "en-US-ChristopherNeural",
        "companion": "en-GB-MiaNeural"
    }

    style = getattr(reya, "style", "companion")
    voice = style_to_voice.get(style, "en-GB-MiaNeural")

    preset = {
        "oracle": {"rate": "+20%", "pitch": "+45Hz"},
        "griot": {"rate": "+0%", "pitch": "-1Hz"},
        "cyberpunk": {"rate": "+10%", "pitch": "+4Hz"},
        "zen": {"rate": "-10%", "pitch": "-4Hz"},
        "detective": {"rate": "-5%", "pitch": "-2Hz"},
        "companion": {"rate": "+0%", "pitch": "+15Hz"},
    }.get(style, {"rate": "+0%", "pitch": "+0Hz"})

    return voice, preset


async def speak_with_voice_style_async(text, reya):
    voice, preset = get_voice_and_preset(reya)

    communicate = edge_tts.Communicate(
        text,
        voice=voice,
        rate=preset.get("rate", "+0%"),
        pitch=preset.get("pitch", "+0Hz"),
        volume=preset.get("volume", "+0%")
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_name = tmp_file.name

    await communicate.save(tmp_name)

    try:
        audio = AudioSegment.from_file(tmp_name, format="mp3")
        play(audio)
    except Exception as e:
        print(f"[ERROR] Playback failed: {e}")

    try:
        os.remove(tmp_name)
    except Exception as e:
        print(f"[Warning] Couldn't delete temp file: {e}")


def speak_with_voice_style(text, reya):
    if not text.strip():
        print("[TTS] Empty text, skipping playback.")
        return
    asyncio.run(speak_with_voice_style_async(text, reya))
