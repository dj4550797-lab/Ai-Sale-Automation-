"""
Flixora AI Sales Automation Agent — Rate Limiting

Simple in-memory rate limiter for Phase 1. 
Replace with Redis-based limiter in production.
"""
import time
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, current_app


class RateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self):
        self._attempts = defaultdict(list)

    def is_rate_limited(self, key, max_attempts, window_seconds):
        """Check if a key has exceeded the rate limit."""
        now = time.time()
        cutoff = now - window_seconds

        # Clean old entries
        self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]

        if len(self._attempts[key]) >= max_attempts:
            return True

        self._attempts[key].append(now)
        return False

    def get_remaining(self, key, max_attempts, window_seconds):
        """Get remaining attempts for a key."""
        now = time.time()
        cutoff = now - window_seconds
        recent = [t for t in self._attempts[key] if t > cutoff]
        return max(0, max_attempts - len(recent))

    def reset(self, key):
        """Reset rate limit for a key."""
        self._attempts.pop(key, None)


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(max_attempts=None, window=None):
    """Decorator to rate-limit a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            _max = max_attempts or current_app.config.get('LOGIN_RATE_LIMIT', 5)
            _window = window or current_app.config.get('LOGIN_RATE_WINDOW', 300)

            key = f'{f.__name__}:{request.remote_addr}'
            if not current_app.config.get('DISABLE_RATE_LIMIT') and rate_limiter.is_rate_limited(key, _max, _window):
                return jsonify({
                    'success': False,
                    'error': 'Too many attempts. Please try again later.'
                }), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator
