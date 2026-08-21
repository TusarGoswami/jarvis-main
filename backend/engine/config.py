import os
from engine.vault import decrypt_key

ASSISTANT_NAME = "JARVIS"

# Fetch API Key securely.
GEMINI_API_KEY = decrypt_key()

if not GEMINI_API_KEY:
    # If vault is missing, try environment variables (good for CI/CD or local setup)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: Gemini API Key not found. Please run 'python setup_encryption.py YOUR_API_KEY' or set GEMINI_API_KEY environment variable.")