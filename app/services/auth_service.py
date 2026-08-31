"""
Flixora AI Sales Automation Agent — Auth Service

Handles user creation, authentication, and password management.
"""
from datetime import datetime, timezone

from app.extensions import db
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger('auth')


def create_admin_user(username, email, password, display_name='Admin'):
    """Create the default admin user if it doesn't exist."""
    existing = User.query.filter_by(username=username).first()
    if existing:
        logger.info(f'Admin user "{username}" already exists.')
        return existing

    user = User(
        username=username,
        email=email,
        display_name=display_name,
        is_active=True,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    logger.info(f'Admin user "{username}" created.')
    return user


def authenticate_user(username, password):
    """Authenticate a user by username/email and password."""
    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()

    if user and user.check_password(password):
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        return user

    return None


def change_password(user, current_password, new_password):
    """Change a user's password after verifying the current one."""
    if not user.check_password(current_password):
        raise ValueError('Current password is incorrect.')

    user.set_password(new_password)
    db.session.commit()
    logger.info(f'Password changed for user "{user.username}".')
    return True
