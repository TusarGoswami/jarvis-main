import os
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
    GROQ_MODEL: str = "llama3-70b-8192"
    GROQ_VISION_MODEL: str = "llama-3.2-11b-vision-preview"
    
    # Secure API Key loading
    @property
    def GEMINI_API_KEY(self) -> str | None:
        key = decrypt_key()
        if not key:
            key = os.getenv("GEMINI_API_KEY")
        return key

    @property
    def GROQ_API_KEY(self) -> str | None:
        return os.getenv("GROQ_API_KEY")

settings = Settings()

