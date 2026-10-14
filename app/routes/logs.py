"""
Flixora AI Sales Automation Agent — System Activity & Runtime Logs Routes
"""
import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required
from app.extensions import db
from app.models import ActivityLog
from app.security.validation import sanitize_string
from app.utils.logger import get_logger

logger = get_logger('logs_routes')
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
    try:
        log_dir = os.path.join(current_app.root_path, '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.abspath(os.path.join(log_dir, target_name))
        
        if not os.path.exists(log_path):
            return []

        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-lines_count:]]
    except Exception as e:
        return [f"Notice: {target_name} is empty or uninitialized ({str(e)})"]


@logs_bp.route('')
@login_required
def index():
    """Render the System Activity Logs & Live Server Logs page."""
    try:
        search_query = sanitize_string(request.args.get('search', ''))
        actor_filter = sanitize_string(request.args.get('actor_type', ''))
        active_tab = request.args.get('tab', 'live')  # 'live' or 'audit'
        log_file = request.args.get('file', 'app')

        audit_logs = []
        try:
            db.session.rollback()
            query = ActivityLog.query
            if search_query:
                query = query.filter(ActivityLog.description.ilike(f"%{search_query}%") | ActivityLog.action.ilike(f"%{search_query}%"))
            if actor_filter:
                query = query.filter_by(actor_type=actor_filter)
            audit_logs = query.order_by(ActivityLog.created_at.desc()).limit(100).all()
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            logger.error(f"Error querying ActivityLog: {e}")
            audit_logs = []

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
    except Exception as err:
        logger.error(f"Error in logs.index: {err}", exc_info=True)
        return render_template(
            'logs/index.html',
            logs=[],
            live_lines=[f"System logs temporarily unavailable: {err}"],
            active_tab='live',
            log_file='app',
            search='',
            actor_type=''
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


@logs_bp.route('/clear-file', methods=['POST'])
@login_required
def clear_file():
    """Truncate a specific log file or all log files."""
    filename = request.form.get('file', 'app')
    allowed_files = {
        'app': 'app.log',
        'ai': 'ai.log',
        'automation': 'automation.log',
        'security': 'security.log'
    }
    log_dir = os.path.join(current_app.root_path, '..', 'logs')
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        pass
    
    if filename == 'all':
        for target in allowed_files.values():
            path = os.path.abspath(os.path.join(log_dir, target))
            if os.path.exists(path):
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Log file cleared by administrator.\n")
                except Exception as e:
                    logger.error(f"Failed to clear {target}: {e}")
        flash("All server runtime log files cleared successfully.", "success")
        return redirect(url_for('logs.index', tab='live'))

    target_name = allowed_files.get(filename, 'app.log')
    target_path = os.path.abspath(os.path.join(log_dir, target_name))
    try:
        if os.path.exists(target_path):
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Log file '{target_name}' cleared by administrator.\n")
        flash(f"Log file '{target_name}' cleared successfully.", "success")
    except Exception as e:
        logger.error(f"Failed to clear log file {target_name}: {e}")
        flash(f"Error clearing log file: {str(e)}", "error")
        
    return redirect(url_for('logs.index', tab='live', file=filename))


@logs_bp.route('/clear-audit', methods=['POST'])
@login_required
def clear_audit():
    """Delete all database activity audit logs."""
    try:
        db.session.rollback()
        deleted = ActivityLog.query.delete()
        db.session.commit()
        flash(f"Cleared {deleted} activity audit records.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to clear activity logs: {e}")
        flash(f"Error clearing audit logs: {str(e)}", "error")
        
    return redirect(url_for('logs.index', tab='audit'))


@logs_bp.route('/clear', methods=['POST'])
@login_required
def clear_all():
    """Clear both file runtime logs and database audit logs."""
    try:
        db.session.rollback()
        ActivityLog.query.delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing activity logs in clear_all: {e}")

    log_dir = os.path.join(current_app.root_path, '..', 'logs')
    for target in ['app.log', 'ai.log', 'automation.log', 'security.log']:
        path = os.path.abspath(os.path.join(log_dir, target))
        if os.path.exists(path):
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] System logs cleared by administrator.\n")
            except Exception as e:
                logger.error(f"Failed to truncate {target}: {e}")

    flash("All runtime logs and database audit records cleared.", "success")
    return redirect(url_for('logs.index'))
