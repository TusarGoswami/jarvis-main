import re
from typing import Any

# Secret and API key patterns
SECRET_PATTERNS = [
    # Google API Keys (AIzaSy...)
    (r"AIza[0-9A-Za-z-_]{25,}", "[REDACTED_GEMINI_KEY]"),
    # Groq API Keys (gsk_...)
    (r"gsk_[0-9A-Za-z-_]{20,}", "[REDACTED_GROQ_KEY]"),
    # Authorization header tokens (Bearer ...)
    (r"(?i)Bearer\s+[A-Za-z0-9\-\._~\+\/]{15,}=*", "Bearer [REDACTED]"),
    # URL query string parameters (key=..., api_key=..., token=..., secret=...)
    (r"(?i)(key|api_key|token|access_token|secret|password)=([^&\s\"'>\[\]]+)", r"\1=[REDACTED]"),
    # Fernet encrypted ciphertexts or keys
    (r"gAAAAA[A-Za-z0-9-_=]{40,}", "[REDACTED_CIPHER]")
]

def sanitize_text(text: Any) -> str:
    """
    Sanitizes arbitrary text, error messages, and URLs to ensure no raw API keys,
    tokens, or passwords can be exposed in logs, exceptions, or client payloads.
    """
    if text is None:
        return ""
    
    clean_str = str(text)
    for pattern, replacement in SECRET_PATTERNS:
        clean_str = re.sub(pattern, replacement, clean_str)
    
    return clean_str
