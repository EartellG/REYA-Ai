import subprocess

# llm_interface.py
def get_response(input_text):
    # If using a local model like Ollama
    import subprocess

    result = subprocess.run(
        ["ollama", "run", "llama3", input_text],
        capture_output=True,
        text=True
    )
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
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,  # Hide error messages
    encoding="utf-8",           # Ensure clean Unicode handling
)
    return result.stdout.strip().lower()
