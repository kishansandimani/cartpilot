"""Encrypts third-party tokens before they touch the database."""
from ..config import get_settings


def _fernet():
    from cryptography.fernet import Fernet
    key = get_settings().encryption_key
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not set, so tokens cannot be stored. See .env.example.")
    return Fernet(key.encode())


def encrypt_token(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_token(cipher: str) -> str:
    return _fernet().decrypt(cipher.encode()).decode()
