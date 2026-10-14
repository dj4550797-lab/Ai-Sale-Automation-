"""
Flixora AI Sales Automation Agent — Agent Performance Routes
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from app.extensions import db
from app.models import CorrectionRule, LLMProvider
from app.security.validation import sanitize_string

performance_bp = Blueprint('performance', __name__, url_prefix='/performance')


@performance_bp.route('')
@login_required
def index():
    """Render the Agent Performance and Correction Rules page."""
    rules = CorrectionRule.query.order_by(CorrectionRule.created_at.desc()).all()
    providers = LLMProvider.query.all()
    return render_template('performance/index.html', rules=rules, providers=providers)


@performance_bp.route('/rules/add', methods=['POST'])
@login_required
def add_rule():
    """Add a new error correction rule manually (§84)."""
    error_type = sanitize_string(request.form.get('error_type', ''))
    error_desc = sanitize_string(request.form.get('error_description', ''))
    cause = sanitize_string(request.form.get('cause', ''))
    correction = sanitize_string(request.form.get('correction', ''))

    if not error_type or not correction:
        flash('Error type and correction instructions are required.', 'error')
        return redirect(url_for('performance.index'))

    try:
        rule = CorrectionRule(
            error_type=error_type,
            error_description=error_desc,
            cause=cause,
            correction=correction,
            is_active=True
        )
        db.session.add(rule)
        db.session.commit()
        flash('Correction rule added successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding rule: {str(e)}", 'error')

    return redirect(url_for('performance.index'))


@performance_bp.route('/rules/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_rule(id):
    """Toggle active state of a correction rule."""
    rule = CorrectionRule.query.get_or_404(id)
    rule.is_active = not rule.is_active
    db.session.commit()
    
    status_str = 'activated' if rule.is_active else 'deactivated'
    return jsonify({
        "success": True,
        "message": f"Rule {rule.id} is now {status_str}.",
        "is_active": rule.is_active
    })
