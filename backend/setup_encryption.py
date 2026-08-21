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
        # Try to migrate key from config if it exists
        try:
            from engine.config import GEMINI_API_KEY
            if GEMINI_API_KEY and "AIza" in str(GEMINI_API_KEY):
                print("Found GEMINI API KEY in config, moving to vault...")
                encrypt_key(GEMINI_API_KEY)
                print("Encryption complete. You can now remove it from config.py.")
            else:
                print("No valid key found in config.")
        except ImportError:
            print("Could not import engine.config.")

        print("\nUsage to encrypt new key: python setup_encryption.py YOUR_API_KEY")
