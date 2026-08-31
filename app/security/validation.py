"""
Flixora AI Sales Automation Agent — Input Validation Helpers
"""
import re
from urllib.parse import urlparse


def is_valid_email(email):
    """Basic email validation."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url):
    """Validate a URL."""
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def is_valid_phone(phone):
    """Basic phone number validation."""
    if not phone:
        return False
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def sanitize_string(text, max_length=500):
    """Sanitize a string input."""
    if not text:
        return ''
    text = str(text).strip()
    # Remove null bytes
    text = text.replace('\x00', '')
    return text[:max_length]


def sanitize_html(text):
    """Strip HTML tags from text."""
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', str(text))
