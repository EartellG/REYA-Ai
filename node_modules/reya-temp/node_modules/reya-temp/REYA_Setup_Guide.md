
# REYA Setup Guide - Responsive Expressive Yielding Assistant

Welcome to the setup guide for **REYA**, your personal AI assistant powered by local models and voice interaction. This guide is written to help **new full stack developers** learn by doing — every step is explained clearly.

---

## 📌 What You'll Build
REYA is a Jarvis-like assistant that runs offline using a local LLM (Mistral via Ollama). She can understand your voice, reply aloud, and handle features like reminders, notes, and more.

---

## 🔧 Tools Required

- **Python 3.10+**
- **Git**
- **Ollama** (for running Mistral)
- **GitHub account**
- **VS Code or any code editor**

---

## 1️⃣ Set Up Your GitHub Repository

1. Go to [GitHub](https://github.com) and log in.
2. Click the **+ icon** in the top-right → **New repository**.
3. Name it something like `reya-assistant`.
4. **Do not check** any boxes for README, .gitignore, or license.
5. Click **Create repository**.

---

## 2️⃣ Clone the Repository Locally

In Git Bash or Terminal:

```bash
cd path/to/your/projects
git clone https://github.com/your-username/reya-assistant.git
cd reya-assistant
```

---

## 3️⃣ Initialize the Python Project

```bash
python -m venv venv         # Create virtual environment
venv\Scripts\activate     # Activate on Windows
pip install --upgrade pip
```

Install the basics:

```bash
pip install openai-whisper pyttsx3
```

Create the project structure:

```bash
mkdir voice features utils
type nul > main.py voice\stt.py voice\tts.py llm_interface.py utils\config.py requirements.txt README.md setup_instructions.md
```

---

## 4️⃣ Install Ollama and Run Mistral

1. Download Ollama from [https://ollama.com/download](https://ollama.com/download)
2. After installing, open a terminal and run:

```bash
ollama run mistral
```

This loads the Mistral model into memory.

---

## 5️⃣ Build REYA's Brain (Starter Code)

### main.py (entry point)
```python
from voice.stt import listen
from voice.tts import speak
from llm_interface import get_response

while True:
    user_input = listen()
    if user_input in ["exit", "quit"]:
        break
    response = get_response(user_input)
    speak(response)
```

### voice/stt.py (speech to text)
```python
import whisper

model = whisper.load_model("base")

def listen():
    print("Listening...")
    result = model.transcribe("input.wav")
    return result["text"]
```

### voice/tts.py (text to speech)
```python
import pyttsx3

engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()
```

### llm_interface.py
```python
import subprocess

def get_response(prompt):
    result = subprocess.run(["ollama", "run", "mistral"], input=prompt, text=True, capture_output=True)
    return result.stdout
```

---

## 6️⃣ Using Git

### First commit:
```bash
git add .
git commit -m "Initial REYA setup"
git push -u origin main
```

### Add a feature branch:
```bash
git checkout -b feature/notes
```

---

## 7️⃣ Running REYA

From your project folder:

```bash
python main.py
```

Say something like “What’s the weather?” and REYA will respond (using the local model and text-to-speech).

---

## ✅ Tips for Expanding REYA

- Add `features/notes.py` for saving notes
- Add `features/reminders.py` with local scheduling (use `sched` or `apscheduler`)
- Connect to calendar or fetch news using `requests`

---

## 🧠 Learn as You Go

- Each module is a mini-app: Voice input, AI response, Voice output
- Git helps track your progress and lets you experiment safely with branches

---

## 💡 You Can Add Later:
- OpenAI GPT-4 support (just add your API key in `.env`)
- Web search plugin
- GUI with PyQt or Gradio

---

**Happy building, and welcome to your REYA journey!**
