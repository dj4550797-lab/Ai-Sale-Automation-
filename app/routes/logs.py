"""
Flixora AI Sales Automation Agent — System Activity Logs Routes
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.extensions import db
from app.models import ActivityLog
from app.security.validation import sanitize_string

logs_bp = Blueprint('logs', __name__, url_prefix='/logs')


@logs_bp.route('')
@login_required
def index():
    """Render the System Activity Logs page."""
    search_query = sanitize_string(request.args.get('search', ''))
    actor_filter = sanitize_string(request.args.get('actor_type', ''))

    query = ActivityLog.query
    
    if search_query:
        query = query.filter(ActivityLog.description.ilike(f"%{search_query}%") | ActivityLog.action.ilike(f"%{search_query}%"))
    if actor_filter:
        query = query.filter_by(actor_type=actor_filter)

    logs = query.order_by(ActivityLog.created_at.desc()).limit(100).all()
    
    return render_template('logs/index.html',
                           logs=logs,
                           search=search_query,
                           actor_type=actor_filter)
