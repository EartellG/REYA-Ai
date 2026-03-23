# backend/voice/xtts_coqui.py
"""
XTTS v2 wrapper for Reya — stable Windows-safe version.
Features:
- Uses your reference WAV to extract conditioning latents.
- Runs xtts.inference() directly (never calls full_inference or load_audio(None)).
- Adds optional AI undertone + clarity boost + stable pitch shift.
- No librosa, no numba, no phase vocoder (avoids Windows crashes).
"""

import os
import threading
from typing import Optional
import torch # type: ignore
import torch.nn.functional as F # type: ignore
import soundfile as sf
from TTS.api import TTS as COQUI_TTS # type: ignore

# ---------------------------------------------------------
# Model & Paths
# ---------------------------------------------------------

XTTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"

# Project root: .../REYA-Ai
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Voice reference WAV (from .env or fallback)
_ref_cfg = os.getenv("REYA_VOICE_SPEAKER_WAV", "backend/voice/reference/reya.wav")
if not os.path.isabs(_ref_cfg):
    VOICE_REF_PATH = os.path.join(PROJECT_ROOT, _ref_cfg.replace("/", os.sep))
else:
    VOICE_REF_PATH = _ref_cfg

TMP_DIR = os.path.join(os.path.dirname(__file__), "tmp_xtts")

VALID_LANGS = [
    "en","es","fr","de","it","pt","pl","tr","ru","nl",
    "cs","ar","zh-cn","hu","ko","ja","hi"
]

LANG_ALIAS = {
    "english": "en",
    "jp": "ja",
    "japanese": "ja",
    "zh": "zh-cn",
    "cn": "zh-cn",
    "mandarin": "zh-cn",
    "chinese": "zh-cn",
}


# ---------------------------------------------------------
#  VOICE PROFILES
# ---------------------------------------------------------

VOICE_PROFILES = {
    "wake": {
        "temperature": 0.65,
        "top_p": 0.85,
        "ai_undertone": 0.02,
        "clarity": 0.04,
        "speed": 1.25,
    },
    "chat": {
        "temperature": 0.85,
        "top_p": 0.95,
        "ai_undertone": 0.04,
        "clarity": 0.02,
        "speed": 1.15,
    },
    "academy": {
        "temperature": 0.68,
        "top_p": 0.80,
        "ai_undertone": 0.02,
        "clarity": 0.06,
        "speed": 0.95,
    },
    "system": {
        "temperature": 0.60,
        "top_p": 0.75,
        "ai_undertone": 0.01,
        "clarity": 0.07,
        "speed": 1.0,
    },
}





# ---------------------------------------------------------
# Caches (model + conditioning latents)
# ---------------------------------------------------------

_tts: Optional[COQUI_TTS] = None
_xtts_model = None
_gpt_latent: Optional[torch.Tensor] = None
_spk_embedding: Optional[torch.Tensor] = None
_lock = threading.Lock()


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _normalize_lang(lang: Optional[str]) -> str:
    if not lang:
        return "en"
    lang = lang.strip().lower()
    lang = LANG_ALIAS.get(lang, lang)
    return lang if lang in VALID_LANGS else "en"


def _get_tts_and_model():
    """Load XTTS v2 only once."""
    global _tts, _xtts_model

    with _lock:
        if _tts is not None and _xtts_model is not None:
            return _tts, _xtts_model

        print("### XTTS: Loading model (CPU mode) ###")
        tts = COQUI_TTS(model_name=XTTS_MODEL, progress_bar=False, gpu=False)
        xtts = tts.synthesizer.tts_model

        _tts = tts
        _xtts_model = xtts
        return _tts, _xtts_model


def _ensure_conditioning_latents():
    """Compute + cache conditioning latents (speaker embedding + GPT latent)."""
    global _gpt_latent, _spk_embedding

    if _gpt_latent is not None:
        return _gpt_latent, _spk_embedding

    tts, xtts = _get_tts_and_model()

    if not os.path.isfile(VOICE_REF_PATH):
        raise FileNotFoundError(
            f"[XTTS] Reference WAV not found: {VOICE_REF_PATH}"
        )

    print(f"[XTTS] Computing conditioning latents from: {VOICE_REF_PATH}")

    cfg = xtts.config
    gpt_latent, spk_embedding = xtts.get_conditioning_latents(
        audio_path=VOICE_REF_PATH,
        max_ref_length=getattr(cfg, "max_ref_len", 10),
        gpt_cond_len=getattr(cfg, "gpt_cond_len", 30),
        gpt_cond_chunk_len=getattr(cfg, "gpt_cond_chunk_len", 6),
        sound_norm_refs=getattr(cfg, "sound_norm_refs", False),
    )

    _gpt_latent = gpt_latent
    _spk_embedding = spk_embedding

    print("[XTTS] Reya conditioning latents cached.")
    return _gpt_latent, _spk_embedding


# ---------------------------------------------------------
# DSP Enhancements (Safe on Windows)
# ---------------------------------------------------------

def _apply_voice_fx(
    wav,
    sample_rate,
    ai_strength: float = 0.03,
    clarity: float = 0.03,
    speed: float = 1.0,
):
    """
    Safe DSP stack:
    - AI undertone (controlled)
    - Prosody smoothing
    - Pitch variance limiter
    - Light clarity boost
    """

    audio = torch.tensor(wav, dtype=torch.float32).unsqueeze(0).unsqueeze(0)

    # 1) AI undertone
    harm_kernel = torch.tensor([[[ -1, 4, -6, 4, -1 ]]], dtype=torch.float32)
    harmonic = F.conv1d(audio, harm_kernel, padding=2)
    audio = audio + ai_strength * harmonic

    # 2) Prosody smoothing
    smooth_kernel = torch.ones(1, 1, 15) / 15
    smoothed = F.conv1d(audio, smooth_kernel, padding=7)
    audio = (audio * 0.80) + (smoothed * 0.20)

    # 3) Pitch variance limiter
    hp_kernel = torch.tensor([[[ -1, 2, -1 ]]], dtype=torch.float32)
    hp = F.conv1d(audio, hp_kernel, padding=1)
    audio = audio - 0.12 * hp

    # 4) Speed / pitch scale
    if speed != 1.0:
        length = audio.shape[-1]
        idx = torch.arange(0, length * speed, speed)
        idx = torch.clamp(idx, 0, length - 1).long()
        audio = audio[:, :, idx]

    # 5) Clarity enhancement
    blur = F.avg_pool1d(audio, kernel_size=7, stride=1, padding=3)
    audio = audio + (audio - blur) * clarity

    return audio.squeeze().numpy()




# ---------------------------------------------------------
# Main XTTS synthesizer
# ---------------------------------------------------------

def synthesize_xtts(
    text: str,
    speaker: Optional[str] = None,
    language: Optional[str] = "en",
    output_path: Optional[str] = None,
    voice_mode: str = "chat",
) -> str:

    if not text or not text.strip():
        raise ValueError("Empty text passed to synthesize_xtts")

    lang = _normalize_lang(language)

    # Output path setup
    if output_path is None:
        os.makedirs(TMP_DIR, exist_ok=True)
        output_path = os.path.join(TMP_DIR, "xtts_output.wav")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Load model + latents
    tts, xtts = _get_tts_and_model()
    gpt_latent, spk_embedding = _ensure_conditioning_latents()


    print(f"[XTTS] Synthesizing: lang={lang}, out={output_path}")
    print("[XTTS] Using Reya's conditioning latents.")

    cfg = xtts.config # type: ignore
    profile = VOICE_PROFILES.get(voice_mode, VOICE_PROFILES["chat"])

    print(
        f"[XTTS] Voice mode: {voice_mode} | "
        f"temp={profile['temperature']} | "
        f"top_p={profile['top_p']} | "
        f"ai={profile['ai_undertone']} | "
        f"clarity={profile['clarity']} | "
        f"speed={profile['speed']}"
)

    # --------------------------------------------
    # Direct XTTS inference (NO full_inference)
    # --------------------------------------------
    out = xtts.inference( # type: ignore
        text=text,
        language=lang,
        gpt_cond_latent=gpt_latent,
        speaker_embedding=spk_embedding,
        temperature=profile["temperature"],     # balanced clarity
        repetition_penalty=10.0,
        top_k=50,
        top_p=profile["top_p"],
        do_sample=True,
    )

    wav = out["wav"]
    sample_rate = getattr(xtts, "output_sample_rate", 24000)

    # --------------------------------------------
    # DSP enhancements (AI undertone + clarity + pitch)
    # --------------------------------------------

    wav = _apply_voice_fx(
        wav,
        sample_rate,
        ai_strength=profile["ai_undertone"],
        clarity=profile["clarity"],
        speed=profile["speed"],
)



    # --------------------------------------------
    # Save to WAV
    # --------------------------------------------
    sf.write(output_path, wav.astype("float32"), sample_rate)

    return os.path.abspath(output_path)


# ---------------------------------------------------------
# URL wrapper for FastAPI
# ---------------------------------------------------------

def synthesize_xtts_to_static_url(
    text: str,
    speaker=None,
    language="en",
    voice_mode: str = "chat",
) -> str:
    from pathlib import Path

    static_dir = Path(__file__).resolve().parent.parent / "static" / "audio"
    static_dir.mkdir(parents=True, exist_ok=True)

    filename = f"reya_{os.urandom(4).hex()}.wav"
    output_path = static_dir / filename

    synthesize_xtts(
        text=text,
        language=language,
        output_path=str(output_path),
        voice_mode=voice_mode,
    )

    return f"/static/audio/{filename}"


def engine_status():
    return {
        "engine": "coqui-xtts",
        "model": XTTS_MODEL,
        "ref_voice": VOICE_REF_PATH,
        "ref_exists": os.path.isfile(VOICE_REF_PATH),
    }
