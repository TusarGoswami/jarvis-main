import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.vault import encrypt_key

if __name__ == "__main__":
    if len(sys.argv) > 1:
        key = sys.argv[1]
        encrypt_key(key)
        print("Encrypted key saved to vault.")
    else:
        try:
            from app.config import settings
            if settings.GEMINI_API_KEY and "AIza" in str(settings.GEMINI_API_KEY):
                print("Found GEMINI API KEY in environment/config, moving to vault...")
                encrypt_key(settings.GEMINI_API_KEY)
                print("Encryption complete.")
            else:
                print("No key found to encrypt.")
        except Exception:
            pass

        print("\nUsage to encrypt new key: python setup_encryption.py YOUR_API_KEY")
