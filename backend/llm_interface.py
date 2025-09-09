# backend/llm_interface.py
import os
import json
import subprocess
from typing import List, Optional

# ------------------------------------------------------------------
# Model selection (single source of truth)
# ------------------------------------------------------------------
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "mistral").strip()            # main chat model
INTENT_MODEL  = os.getenv("OLLAMA_INTENT_MODEL", DEFAULT_MODEL).strip() # tiny/fast classifier

# ------------------------------------------------------------------
# Ollama helpers
# ------------------------------------------------------------------
def _ollama_list() -> List[str]:
    """
    Return installed model names. Tries JSON lines first, falls back to table parsing.
    """
    # Try JSON (newer ollama versions)
    try:
        p = subprocess.run(
            ["ollama", "list", "--json"],
            capture_output=True, text=True, check=True,
            encoding="utf-8", errors="replace"
        )
        names: List[str] = []
        for line in p.stdout.splitlines():
            try:
                row = json.loads(line)
                name = row.get("name")
                if name:
                    names.append(name)
            except json.JSONDecodeError:
                pass
        if names:
            return names
    except Exception:
        pass

    # Fallback: parse the plain table output
    try:
        p = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, check=True,
            encoding="utf-8", errors="replace"
        )
        out: List[str] = []
        for i, ln in enumerate(p.stdout.splitlines()):
            if i == 0:  # skip header line: NAME  ID  SIZE  MODIFIED
                continue
            parts = ln.split()
            if parts:
                out.append(parts[0])
        return out
    except Exception:
        return []

def get_installed_models() -> List[str]:
    return _ollama_list()

def get_default_model() -> str:
    return DEFAULT_MODEL

# ------------------------------------------------------------------
# Single safe query function
# ------------------------------------------------------------------
def query_ollama(prompt: str, model: Optional[str] = None) -> str:
    """
    Run `ollama run <model>` with the prompt on STDIN.
    - No shell=True (portable & safe).
    - Force UTF-8 decoding on Windows to avoid UnicodeDecodeError.
    """
    use_model = (model or DEFAULT_MODEL).strip()
    try:
        p = subprocess.run(
            ["ollama", "run", use_model],
            input=prompt,
            capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace"
        )
        out = p.stdout.strip()
        if out:
            return out
        err = (p.stderr or "").strip()
        return f"[ollama:{use_model} error] {err}" if err else "[ollama] empty response"
    except Exception as e:
        return f"[ollama:{use_model} exception] {e}"

# ------------------------------------------------------------------
# Prompting / persona
# ------------------------------------------------------------------
def get_structured_reasoning_prompt(user_input, context, reya=None) -> str:
    """
    Build a concise REYA prompt that respects personality and recent context.
    """
    # Flatten recent context (adjust to your memory shape if needed)
    ctx_lines: List[str] = []
    if isinstance(context, list):
        for item in context[-4:]:  # last few turns
            try:
                u = (item.get("user_input") or "").strip()
                a = (item.get("assistant_response") or "").strip()
                if u or a:
                    ctx_lines.append(f"User: {u}\nReya: {a}")
            except Exception:
                ctx_lines.append(str(item))
    context_str = "\n\n".join(ctx_lines) or "(none)"

    traits = mannerisms = style = "default"
    if reya:
        p = reya.describe()
        traits = ", ".join(p.get("traits", [])) or "default"
        mannerisms = ", ".join(p.get("mannerisms", [])) or "default"
        style = p.get("style", "default")

    return f"""You are REYA, an AI assistant with personality traits: {traits}, speaking in a "{style}" style.
You often express yourself using mannerisms like: {mannerisms}.

Guidelines:
- Be brief and clear first; offer details if the user asks.
- Use prior context only when it directly helps.
- Keep tone consistent with your personality.

Context (recent):
{context_str}

User: {user_input}

Reya:"""

# ------------------------------------------------------------------
# High-level helpers used by the API
# ------------------------------------------------------------------
def get_response(user_input, reya, history):
    prompt = get_structured_reasoning_prompt(user_input, history, reya=reya)
    return query_ollama(prompt, model=DEFAULT_MODEL)

def classify_intent(text: str) -> str:
    """
    Tiny classifier for routing. Uses INTENT_MODEL by default.
    """
    system = (
        "You are an intent classifier for a voice assistant.\n"
        "Given a user's command, answer with one label exactly:\n"
        "note | reminder | web_search | greeting | exit"
    )
    prompt = f"{system}\nUser: {text}\nIntent:"
    return query_ollama(prompt, model=INTENT_MODEL)
