"""
Flixora AI Sales Automation Agent — Time Utilities
"""
from datetime import datetime, timezone, timedelta


def utc_now():
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def format_relative(dt):
    """Format a datetime as a human-readable relative string."""
    if dt is None:
        return 'Never'

    now = utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt

    if diff.total_seconds() < 0:
        return 'In the future'
    if diff.total_seconds() < 60:
        return 'Just now'
    if diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f'{minutes} min ago'
    if diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f'{hours}h ago'
    if diff.days == 1:
        return 'Yesterday'
    if diff.days < 7:
        return f'{diff.days} days ago'
    if diff.days < 30:
        weeks = diff.days // 7
        return f'{weeks}w ago'
    if diff.days < 365:
        months = diff.days // 30
        return f'{months}mo ago'

    years = diff.days // 365
    return f'{years}y ago'


def format_datetime(dt, fmt='%Y-%m-%d %H:%M'):
    """Format a datetime object."""
    if dt is None:
        return ''
    return dt.strftime(fmt)


def parse_datetime(text, fmt='%Y-%m-%dT%H:%M'):
    """Parse a datetime string."""
    try:
        return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
