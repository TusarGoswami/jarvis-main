import os
from typing import Optional
from cryptography.fernet import Fernet

# Key stored outside project root for security
_JARVIS_DIR = os.path.join(os.path.expanduser("~"), ".jarvis")
os.makedirs(_JARVIS_DIR, exist_ok=True)
KEY_FILE = os.path.join(_JARVIS_DIR, ".key")

# Vault stays in the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_FILE = os.path.join(BASE_DIR, ".vault")

def get_crypto_key():
    """Load or generate a master key for encryption."""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key

def encrypt_key(plain_text: str):
    """Encrypt a string and save it to the vault."""
    f = Fernet(get_crypto_key())
    cipher_text = f.encrypt(plain_text.encode())
    with open(VAULT_FILE, "wb") as v:
        v.write(cipher_text)
    return cipher_text

def decrypt_key():
    """Load the encrypted key from the vault and decrypt it."""
    if not os.path.exists(VAULT_FILE):
        return None
    
    f = Fernet(get_crypto_key())
    with open(VAULT_FILE, "rb") as v:
        cipher_text = v.read()
    
    try:
        return f.decrypt(cipher_text).decode()
    except Exception:
        return None

def encrypt_data(plain_text: Optional[str]) -> Optional[str]:
    """Encrypt a string payload and return a tagged 'enc::' token."""
    if plain_text is None:
        return None
    if isinstance(plain_text, str) and plain_text.startswith("enc::"):
        return plain_text
    
    f = Fernet(get_crypto_key())
    token = f.encrypt(plain_text.encode("utf-8")).decode("utf-8")
    return f"enc::{token}"

def decrypt_data(cipher_text: Optional[str]) -> Optional[str]:
    """
    Decrypts an 'enc::' tagged token back to plaintext.
    Gracefully returns plaintext if the string is unencrypted (legacy data fallback).
    """
    if cipher_text is None:
        return None
    if not isinstance(cipher_text, str) or not cipher_text.startswith("enc::"):
        return cipher_text
    
    token = cipher_text[5:]
    f = Fernet(get_crypto_key())
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        # Fallback in case of corruption or unencrypted content
        return cipher_text


