import subprocess

def get_response(prompt):
    result = subprocess.run(["ollama", "run", "mistral"], input=prompt, text=True, capture_output=True)
    return result.stdout

def classify_intent(prompt: str) -> str:
    system_prompt = """
You are an intent classifier for a voice assistant.
Given a user's command, respond with one of the following intents:
- "note"
- "reminder"
- "web_search"
- "greeting"
- "exit"
Only return the intent label.
"""
    input_text = f"{system_prompt}\nUser: {prompt}\nIntent:"
    result = subprocess.run(
        ["ollama", "run", "mistral"],
        input=input_text,
        text=True,
        capture_output=True
    )
    return result.stdout.strip().lower()
