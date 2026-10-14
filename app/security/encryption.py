"""
Flixora AI Sales Automation Agent — Credential Encryption

Fernet symmetric encryption for API keys and secrets stored in the database.
Secrets are encrypted before storage and decrypted only at runtime.
"""
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from app.utils.logger import get_logger

logger = get_logger('security')


def _get_fernet():
    """Get Fernet instance from the configured encryption key."""
    key = current_app.config.get('ENCRYPTION_KEY', '')
    if not key:
        raise ValueError('ENCRYPTION_KEY is not configured. Set it in .env')
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        raise ValueError(f'Invalid ENCRYPTION_KEY format: {e}')


def encrypt_value(plaintext):
    """Encrypt a plaintext string. Returns encrypted bytes as string."""
    if not plaintext:
        return ''
    f = _get_fernet()
    encrypted = f.encrypt(plaintext.encode('utf-8'))
    return encrypted.decode('utf-8')


def decrypt_value(encrypted_text):
    """Decrypt an encrypted string. Returns plaintext."""
    if not encrypted_text:
        return ''
    f = _get_fernet()
    try:
        if isinstance(encrypted_text, str):
            encrypted_text = encrypted_text.encode('utf-8')
        decrypted = f.decrypt(encrypted_text)
        return decrypted.decode('utf-8')
    except InvalidToken:
        logger.error('Failed to decrypt value — invalid token or wrong key')
        raise ValueError('Failed to decrypt credential. The encryption key may have changed.')


def generate_encryption_key():
    """Generate a new Fernet encryption key (for initial setup)."""
    return Fernet.generate_key().decode('utf-8')
