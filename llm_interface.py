import subprocess

def query_ollama(prompt: str, model: str = "llama3") -> str:
    try:
        result = subprocess.run(
            f'echo {prompt!r} | ollama run {model}',
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        return result.stdout.strip()
    except Exception as e:
        return f"[Error querying Ollama]: {e}"


# Main function to get a response from the assistant
def get_response(user_input, history):
    prompt = get_structured_reasoning_prompt(user_input, history)
    return query_ollama(prompt, model="llama3")  # You can change this model

# Classify user intent using a lightweight model
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
    full_prompt = f"{system_prompt}\nUser: {prompt}\nIntent:"
    return query_ollama(full_prompt, model="mistral")  # Use a small model for speed

# Build the structured reasoning prompt from memory
def get_structured_reasoning_prompt(user_input, history):
    context = "\n".join(
        [f"User: {item['user_input']}\nReya: {item['assistant_response']}" for item in history]
    )

    prompt = f"""You are REYA, a helpful and logical AI assistant. Answer the user's latest question clearly and concisely using prior context only if relevant.

{context}

User: {user_input}
Reya:"""
    return prompt

