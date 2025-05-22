from features.web_search import search_web
from voice.edge_tts import speak_with_voice_style
from reya_personality import ReyaPersonality, TRAITS, MANNERISMS, STYLES

query = "What is the capital of Japan"
result = search_web(query)
print(f"📄 Result: {result}")



reya = ReyaPersonality(
    traits=[TRAITS["stoic"], TRAITS["playful"]],
    mannerisms=[MANNERISMS["sassy"], MANNERISMS["meta_awareness"]],
    style=STYLES["oracle"],
    voice="en-US-AriaNeural",  # pick any Edge TTS voice you like
    preset={
        "rate": "-15%",    # slower speech
        "pitch": "-5Hz",   # deeper pitch
        "volume": "+0%"    # normal volume
    }
)

speak_with_voice_style(result, reya)