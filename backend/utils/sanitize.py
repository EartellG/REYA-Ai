# backend/utils/sanitize.py
import re

_DIAG_RE = re.compile(r"\bdiag\s*:\s*\w+\s*=\s*[^,\n]+", re.IGNORECASE)
_SECRET_RE = re.compile(r"(password[_\s-]*hash|api[_\s-]*key|token)\s*[:=]\s*[^,\n]+", re.IGNORECASE)

def sanitize_response(text: str) -> str:
    """
    Scrub accidental debug/diagnostic key-value pairs and obvious secrets
    from model output before sending to the UI / TTS.
    """
    if not text:
        return text
    # Remove diag:key=value fields the model might invent
    text = _DIAG_RE.sub("[redacted]", text)
    # Remove any obvious secrets pattern if hallucinated
    text = _SECRET_RE.sub("[redacted]", text)
    return text
