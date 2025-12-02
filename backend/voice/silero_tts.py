# backend/voice/silero_tts.py
# Offline Silero TTS fallback (English)
# Used automatically when Azure/Edge are unavailable.

import torch
import os
from pathlib import Path

# ---------------------- Output directory ----------------------
AUDIO_DIR = Path(__file__).resolve().parent.parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------- Globals ----------------------
_model = None
_speaker = "v3_en"     # consistent with main engine
_sample_rate = 48000


def _load_model():
    """Load and cache Silero model (only once)."""
    global _model
    if _model is not None:
        return _model

    try:
        torch.set_num_threads(4)
        device = torch.device("cpu")

        print("[Silero] 🔊 Loading Silero TTS model (en)...")
        model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="en",
            speaker=_speaker
        ) # type: ignore
        _model = model.to(device)
        print("[Silero] ✅ Model loaded and ready.")
        return _model
    except Exception as e:
        print(f"[Silero] ❌ Failed to load: {e}")
        _model = None
        return None


def synthesize_silero(text: str, out_path: str = "") -> str:
    """Generate speech with Silero and save to file (WAV)."""
    if not text:
        raise ValueError("Empty text provided to Silero TTS")

    model = _load_model()
    if model is None:
        raise RuntimeError("Silero model could not be loaded.")

    wav_path = Path(out_path) if out_path else AUDIO_DIR / f"silero_{os.getpid()}.wav"
    try:
        model.save_wav(
            text=text,
            speaker=_speaker,
            sample_rate=_sample_rate,
            audio_path=str(wav_path)
        )
        return str(wav_path)
    except Exception as e:
        print(f"[Silero] ❌ Generation failed: {e}")
        raise
