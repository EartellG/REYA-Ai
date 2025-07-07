# REYA-AI Prototype
python -m uvicorn backend.api:app --reload --port 8000
Npm run Dev.

Welcome to the REYA-AI Assistant Prototype! This project is a voice-enabled, logic-aware, language-learning AI assistant with a modular architecture.

---

## 🧠 Features

- **Voice Interaction (Edge-TTS)**: Speaks with personality-based voice styles (Oracle, Griot, Zen...)
- **Wake Word Detection + STT**: Say "Hey REYA" to activate voice loop
- **Language Tutor**: Teaches Japanese and Mandarin with vocab tracking
- **Reasoning Engine**: Handles logical prompts and symbolic queries
- **Code Help**: Searches StackOverflow
- **Web Search + Reddit + YouTube Metadata**

---

## ⚙️ Setup

### 1. Python Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Make sure `ffmpeg` is installed and available in PATH

# Run backend server (FastAPI)
python -m uvicorn backend.api:app --reload --port 8000

# Or run REYA's voice loop directly
cd backend
python main.py
```

### 2. Node/React Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Known Issues

- 🟡 **Edge-TTS sometimes fails to speak**: Try using `pygame` or log the path for debugging.
- 🔇 **No mic detected**: Make sure you have an input device plugged in. Windows audio settings must allow mic access.
- 🌀 **Streaming chat not appearing**: Confirm frontend is using ReadableStream to fetch `/chat` endpoint.
- 🧠 **Memory not saving**: Ensure `memory/user_context.json` is writable.

---

## 🧪 Test Commands

```txt
"Teach me Japanese"         → Launches tutor
"Quiz me in Mandarin"       → Vocabulary quiz
"What do you remember?"     → Recalls memory log
"Search YouTube for..."     → Gets title of video
"What's true and not false" → Logic check
"Goodbye"                   → Ends REYA loop
```

---

## 🧰 Dev Tips

- All features are modular: `features/`, `voice/`, `utils/`
- Modify `reya_personality.py` to change her vibe
- `ContextualMemory` stores recent memory, traits, preferences, and vocab

---

## 📦 Deployment Prep

- Zip the entire `REYA-Ai` folder
- Include:
  - `backend/`
  - `frontend/`
  - `README.md`
  - `requirements.txt`
  - `memory/user_context.json` (empty if needed)

---

Made with ❤️ by [you].