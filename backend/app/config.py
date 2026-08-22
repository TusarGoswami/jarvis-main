import os
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from engine.vault import decrypt_key

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = os.path.dirname(_BASE_DIR)

# Load .env file from backend or root
load_dotenv(os.path.join(_BASE_DIR, ".env"))
load_dotenv(os.path.join(_ROOT_DIR, ".env"))

class Settings(BaseModel):
    ASSISTANT_NAME: str = "Vocalis AI"
    APP_VERSION: str = "2.0.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8005
    DEBUG: bool = True
    WORKSPACE_DIR: str = os.path.join(_BASE_DIR, "workspace")
    
    # Model configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    FALLBACK_MODEL: str = "gemini-1.5-flash"
    GROQ_MODEL: str = "qwen/qwen3.6-27b"
    GROQ_VISION_MODEL: str = "openai/gpt-oss-20b"

    # Calendar Voice Alert Configuration
    DEFAULT_MEETING_ALERT_MINUTES: int = int(os.getenv("MEETING_ALERT_MINUTES", "10"))

    
    # Secure Multi-API Key loading with automatic failover
    @property
    def GEMINI_API_KEYS(self) -> List[str]:
        keys: List[str] = []
        # Check vault
        v_key = decrypt_key()
        if v_key and v_key not in keys:
            keys.append(v_key)
        # Check primary GEMINI_API_KEY
        k1 = os.getenv("GEMINI_API_KEY")
        if k1 and k1 not in keys:
            keys.append(k1)
        # Check GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.
        for i in range(2, 50):
            ki = os.getenv(f"GEMINI_API_KEY_{i}")
            if ki and ki not in keys:
                keys.append(ki)
        # Check comma-separated in GEMINI_API_KEYS
        multi = os.getenv("GEMINI_API_KEYS")
        if multi:
            for k in multi.split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)
        return keys

    @property
    def GEMINI_API_KEY(self) -> Optional[str]:
        keys = self.GEMINI_API_KEYS
        return keys[0] if keys else None

    @property
    def GROQ_API_KEY(self) -> Optional[str]:
        return os.getenv("GROQ_API_KEY")

settings = Settings()
