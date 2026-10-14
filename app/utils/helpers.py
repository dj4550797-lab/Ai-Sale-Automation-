"""
Flixora AI Sales Automation Agent — Helper Utilities
"""
import math
import re
import uuid
from datetime import datetime, timezone


def generate_uuid():
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def slugify(text):
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text


def truncate(text, length=100, suffix='...'):
    """Truncate text to specified length."""
    if not text:
        return ''
    if len(text) <= length:
        return text
    return text[:length - len(suffix)] + suffix


def mask_secret(value, visible_chars=4):
    """Mask a secret value, showing only the last few characters."""
    if not value:
        return ''
    if len(value) <= visible_chars:
        return '•' * len(value)
    return '•' * (len(value) - visible_chars) + value[-visible_chars:]


def format_number(n):
    """Format a number with commas (e.g., 1,234,567)."""
    if n is None:
        return '0'
    return f'{n:,}'


def format_currency(amount, currency='₹'):
    """Format an amount as currency."""
    if amount is None:
        return f'{currency}0'
    return f'{currency}{amount:,.2f}'


def paginate_query(query, page=1, per_page=20):
    """Apply pagination to a SQLAlchemy query and return metadata."""
    page = max(1, page)
    per_page = min(per_page, 100)

    total = query.count()
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    page = min(page, total_pages)

    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        'items': items,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
    }


def safe_int(value, default=0):
    """Safely convert a value to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    """Safely convert a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
