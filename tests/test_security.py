"""
Flixora AI Sales Automation Agent — Security & Encryption Tests
"""
import pytest
from app import create_app
from app.security.encryption import encrypt_value, decrypt_value, generate_encryption_key
from app.utils.helpers import mask_secret


def test_encryption_decryption():
    """Test that value encryption and decryption work correctly."""
    app = create_app('testing')
    
    with app.app_context():
        # Set a test encryption key
        key = generate_encryption_key()
        app.config['ENCRYPTION_KEY'] = key
        
        original_value = "my-secret-api-key-12345"
        encrypted = encrypt_value(original_value)
        
        assert encrypted != original_value
        assert len(encrypted) > 0
        
        decrypted = decrypt_value(encrypted)
        assert decrypted == original_value


def test_encryption_invalid_key():
    """Test encryption behavior with missing/invalid key."""
    app = create_app('testing')
    
    with app.app_context():
        app.config['ENCRYPTION_KEY'] = ''
        with pytest.raises(ValueError, match="ENCRYPTION_KEY is not configured"):
            encrypt_value("secret")


def test_mask_secret():
    """Test secret masking utility."""
    secret = "sk-proj-1234567890abcdef"
    masked = mask_secret(secret, visible_chars=4)
    assert masked.endswith("cdef")
    assert masked.startswith("••••")
    assert len(masked) == len(secret)
    
    short_secret = "abc"
    assert mask_secret(short_secret) == "•••"
    assert mask_secret(None) == ""
