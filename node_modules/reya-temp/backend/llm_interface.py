import subprocess
from reya_personality import ReyaPersonality

reya_personality = ReyaPersonality()

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
    """
    Build a prompt focused on answering the current question,
    using prior context only if it's clearly relevant.
    Includes guidance to give a short answer first and offer details if needed.
    """
    # Grab last 2 interactions if available
    recent_items = history[-2:] if isinstance(history, list) else []

    context_block = ""
    for item in recent_items:
        response = item["assistant_response"].strip()
        # Filter out garbage responses that still contain "You are REYA"
        if "You are REYA" in response:
            continue
        context_block += f"User: {item['user_input'].strip()}\nReya: {response}\n"

       

    # Base instructions
    instructions = (
        "Answer the user's current question briefly and clearly.\n"
        "If the answer is complex, give a short summary first and ask if they want a detailed explanation.\n"
        "Only use previous context if it directly helps answer the question.\n\n"
    )

    # Build final prompt
    prompt = ""
    if context_block:
        prompt += f"Relevant past context:\n{context_block.strip()}\n\n"

    prompt += instructions
    prompt += f"User: {user_input.strip()}\nReya:"
    return prompt.strip()

# ✅ Patch for full integration of REYA's personality into structured LLM prompts

# --- llm_interface.py ---
from reya_personality import ReyaPersonality

# Accept the ReyaPersonality instance in prompt generation
def get_structured_reasoning_prompt(user_input, context, reya=None):
    context_str = "\n".join(str(item) for item in (context or []))


    # Extract personality info
    if reya:
        personality = reya.describe()
        traits = ", ".join(personality['traits'])
        mannerisms = ", ".join(personality['mannerisms'])
        style = personality['style']
    else:
        traits = mannerisms = style = "default"

    prompt = f"""
You are REYA, an AI assistant with personality traits: {traits}, speaking in a "{style}" style.
You often express yourself using mannerisms like: {mannerisms}.

Your goals:
- Stay true to your personality and mannerisms.
- Be relevant, helpful, and engaging.
- Match your tone to the user's energy.
- Reference the conversation context when helpful.

Context:
{context_str}

User said: "{user_input}"

Respond as REYA:
"""
    return prompt

def get_response(user_input, history):
    prompt = get_structured_reasoning_prompt(user_input, history, reya=reya_personality)
    return query_ollama(prompt, model="llama3")