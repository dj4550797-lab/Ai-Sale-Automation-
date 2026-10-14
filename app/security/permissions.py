"""
Flixora AI Sales Automation Agent — Permission Checks
"""
from flask_login import current_user
from app.constants import RiskLevel


def can_perform_action(action, risk_level=RiskLevel.LOW):
    """Check if the current context is allowed to perform an action."""
    if not current_user or not current_user.is_authenticated:
        return False

    # Admin can do everything
    if current_user.is_active:
        return True

    return False


def require_approval(risk_level):
    """Check if an action at this risk level requires admin approval."""
    return risk_level == RiskLevel.HIGH
