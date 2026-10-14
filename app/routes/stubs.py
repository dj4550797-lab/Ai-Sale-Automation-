"""
Flixora AI Sales Automation Agent — Stub Routes

Placeholder routes for modules coming in later phases.
Each renders an empty state template with a helpful message.
"""
from flask import Blueprint, render_template
from flask_login import login_required

# ── Leads ──────────────────────────────────────────────────────
leads_bp = Blueprint('leads', __name__, url_prefix='/leads')

@leads_bp.route('')
@login_required
def index():
    return render_template('stub.html', page_title='Leads',
        icon='group', message='Lead database coming in Phase 3.',
        description='Discover, research, and qualify local businesses.')

@leads_bp.route('/discover')
@login_required
def discover():
    return render_template('stub.html', page_title='Lead Discovery',
        icon='search', message='Lead discovery coming in Phase 3.',
        description='Configure location, category, and daily target to discover businesses.')

@leads_bp.route('/qualification')
@login_required
def qualification():
    return render_template('stub.html', page_title='Lead Qualification',
        icon='fact_check', message='Lead qualification coming in Phase 4.',
        description='Score and prioritize leads based on business analysis.')















# ── Notifications API ─────────────────────────────────────────
notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notifications_bp.route('')
@login_required
def index():
    from app.models import Notification
    from flask_login import current_user
    from flask import jsonify

    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(20).all()

    return jsonify({
        'success': True,
        'data': [{
            'id': n.id,
            'type': n.type,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat() if n.created_at else None,
        } for n in notifications]
    })
