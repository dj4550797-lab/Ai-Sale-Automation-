"""
Flixora AI Sales Automation Agent — Logging Utilities

Structured logging with secret filtering. Secrets are never written to logs.
"""
import logging
import os
import re
from logging.handlers import RotatingFileHandler


# Patterns that look like secrets
SECRET_PATTERNS = [
    re.compile(r'(api[_-]?key|apikey|secret|token|password|credential|authorization)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),
    re.compile(r'AIza[a-zA-Z0-9_-]{35}'),
]


class SecretFilter(logging.Filter):
    """Filter that redacts potential secrets from log messages."""

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern in SECRET_PATTERNS:
                record.msg = pattern.sub('[REDACTED]', record.msg)
        if record.args:
            filtered_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern in SECRET_PATTERNS:
                        arg = pattern.sub('[REDACTED]', arg)
                filtered_args.append(arg)
            record.args = tuple(filtered_args)
        return True


def setup_logging(app):
    """Configure application logging with rotating file handlers."""
    log_dir = app.config.get('LOG_DIR', 'logs')
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)

    os.makedirs(log_dir, exist_ok=True)

    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    secret_filter = SecretFilter()

    # Log configurations: (name, filename)
    log_configs = [
        ('flixora', 'app.log'),
        ('flixora.ai', 'ai.log'),
        ('flixora.automation', 'automation.log'),
        ('flixora.security', 'security.log'),
    ]

    for logger_name, filename in log_configs:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.addFilter(secret_filter)

        # File handler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, filename),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(secret_filter)
        logger.addHandler(file_handler)

    # Also configure the root app logger
    app.logger.setLevel(log_level)
    app.logger.addFilter(secret_filter)

    # Console handler for development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(secret_filter)
        app.logger.addHandler(console_handler)

    app.logger.info('Flixora logging initialized.')


def get_logger(name):
    """Get a namespaced logger."""
    return logging.getLogger(f'flixora.{name}')
