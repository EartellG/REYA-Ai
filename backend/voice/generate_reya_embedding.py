import os
import torch
import torchaudio
from TTS.api import TTS

# ====================================
# Paths
# ====================================
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

VOICE_WAV = r"C:\Users\Sydne.YAYU\REYA-Ai\backend\voice\reference\reya.wav"

OUTPUT_DIR = r"C:\Users\Sydne.YAYU\REYA-Ai\backend\voice\reya_embed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUT_EMBED = os.path.join(OUTPUT_DIR, "reya_emb.pt")

# ====================================
# Load XTTS
# ====================================
print("Loading XTTS model…")
tts = TTS(model_name=MODEL_NAME, progress_bar=False, gpu=False)

model = tts.synthesizer.tts_model
encoder = model.hifigan_decoder.speaker_encoder

print("Speaker encoder located:", type(encoder).__name__)

# ====================================
# Load voice audio
# ====================================
print("Loading reference audio…")

audio, sr = torchaudio.load(VOICE_WAV)

# Resample if needed
TARGET_SR = 16000
if sr != TARGET_SR:
    print(f"Resampling from {sr} → {TARGET_SR}")
    resampler = torchaudio.transforms.Resample(sr, TARGET_SR)
    audio = resampler(audio)
    sr = TARGET_SR

# Convert to mono if stereo
if audio.shape[0] > 1:
    print("Converting stereo → mono")
    audio = audio.mean(dim=0, keepdim=True)

# ====================================
# Compute embedding
# ====================================
print("Computing speaker embedding…")

with torch.no_grad():
    emb = encoder(audio)          # XTTS v2 returns ONLY the embedding
    emb = emb.squeeze()           # Remove batch dimensions for clean storage

# Save embedding
torch.save(emb, OUT_EMBED)

print("====================================")
print("Reya voice embedding created!")
print("Saved to:", OUT_EMBED)
print("Embedding shape:", emb.shape)
print("====================================")
