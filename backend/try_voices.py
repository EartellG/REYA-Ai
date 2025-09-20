import asyncio, tempfile, os
import edge_tts

CANDIDATES = [
    "en-GB-SoniaNeural",  # your first choice
    "en-GB-LibbyNeural",
    "en-GB-MiaNeural",
    "en-GB-SophieNeural",
    "en-GB-SusanNeural",
    "en-US-AriaNeural",   # safe female fallbacks
    "en-US-AnaNeural",
    "en-US-MichelleNeural",
    "en-US-JennyNeural",
]

async def try_one(v):
    text = f"This is a quick sample for {v.replace('Neural','')}."
    mp3 = os.path.join(tempfile.gettempdir(), f"{v}.mp3")
    try:
        await edge_tts.Communicate(text, voice=v).save(mp3)
        print(f"✅ Works: {v} -> {mp3}")
        return v
    except Exception as e:
        print(f"⛔ {v}: {e}")
        return None

async def main():
    for v in CANDIDATES:
        ok = await try_one(v)
        if ok:
            print(f"\n➡ Using: {ok}")
            return
    print("\nNo candidate voices worked.")

asyncio.run(main())
