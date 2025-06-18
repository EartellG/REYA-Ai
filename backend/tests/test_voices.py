import asyncio
import edge_tts
from pydub import AudioSegment
from pydub.playback import play



# Set test phrase
TEST_LINE = "Hello, I'm REYA. Let's make something magical together."

# Voices you want to test (filter down if needed)
VOICE_LIST = [
    "en-US-JennyNeural"
    # "en-US-AriaNeural",
    # "en-US-GuyNeural",
    # "en-GB-LibbyNeural",
    # "en-GB-RyanNeural",
    # "en-AU-NatashaNeural",
    # "en-IE-ConnorNeural",
    # "en-NZ-MollyNeural",
]

# Optional: Add some REYA-style presets
VOICE_PRESETS = {
    "oracle": {"rate": "-10%", "pitch": "-5Hz", "volume": "+0%"},
    "zen": {"rate": "-5%", "pitch": "+0Hz", "volume": "+0%"},
    "cyberpunk": {"rate": "+10%", "pitch": "+10Hz", "volume": "+5%"},
    "companion": {"rate": "+0%", "pitch": "+5Hz", "volume": "+5%"},
    "teacher": {"rate": "+5%", "pitch": "+0Hz", "volume": "+0%"},
}

async def test_voice(voice, style):
    print(f"\n🎙️ Voice: {voice} | Style: {style}")
    preset = VOICE_PRESETS.get(style, {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"})
    
    communicate = edge_tts.Communicate(
        text=TEST_LINE,
        voice=voice,
        rate=preset["rate"],
        volume=preset["volume"],
        pitch=preset["pitch"]
    )
    
    file_name = f"voice_test_{style}.wav"
    await communicate.save(file_name)
    sound = AudioSegment.from_file(file_name, format="wav")
    play(sound)



async def main():
    for voice in VOICE_LIST:
        for style in VOICE_PRESETS:
            await test_voice(voice, style)
            await asyncio.sleep(1)  # Pause between tests

if __name__ == "__main__":
    asyncio.run(main())
