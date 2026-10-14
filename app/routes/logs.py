"""
Flixora AI Sales Automation Agent — System Activity & Runtime Logs Routes
"""
import os
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from app.extensions import db
from app.models import ActivityLog
from app.security.validation import sanitize_string

logs_bp = Blueprint('logs', __name__, url_prefix='/logs')


def _read_tail_log(filename, lines_count=150):
    """Safely read the last lines_count lines from a log file."""
    allowed_files = {
        'app': 'app.log',
        'ai': 'ai.log',
        'automation': 'automation.log',
        'security': 'security.log'
    }
    target_name = allowed_files.get(filename, 'app.log')
    log_dir = os.path.join(current_app.root_path, '..', 'logs')
    log_path = os.path.abspath(os.path.join(log_dir, target_name))
    
    if not os.path.exists(log_path):
        return []

    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-lines_count:]]
    except Exception as e:
        return [f"Error reading {target_name}: {str(e)}"]


@logs_bp.route('')
@login_required
def index():
    """Render the System Activity Logs & Live Server Logs page."""
    search_query = sanitize_string(request.args.get('search', ''))
    actor_filter = sanitize_string(request.args.get('actor_type', ''))
    active_tab = request.args.get('tab', 'live')  # 'live' or 'audit'
    log_file = request.args.get('file', 'app')

    query = ActivityLog.query
    if search_query:
        query = query.filter(ActivityLog.description.ilike(f"%{search_query}%") | ActivityLog.action.ilike(f"%{search_query}%"))
    if actor_filter:
        query = query.filter_by(actor_type=actor_filter)

    audit_logs = query.order_by(ActivityLog.created_at.desc()).limit(100).all()
    live_lines = _read_tail_log(log_file, lines_count=150)

    return render_template(
        'logs/index.html',
        logs=audit_logs,
        live_lines=live_lines,
        active_tab=active_tab,
        log_file=log_file,
        search=search_query,
        actor_type=actor_filter
    )


@logs_bp.route('/live-stream')
@login_required
def live_stream():
    """Return JSON tail lines for a specific log file."""
    filename = request.args.get('file', 'app')
    limit = min(int(request.args.get('limit', 150)), 500)
    lines = _read_tail_log(filename, lines_count=limit)
    return jsonify({
        "success": True,
        "file": filename,
        "lines": lines
    })
