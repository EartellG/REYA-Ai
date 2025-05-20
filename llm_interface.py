import subprocess

def get_response(prompt):
    result = subprocess.run(["ollama", "run", "mistral"], input=prompt, text=True, capture_output=True)
    return result.stdout