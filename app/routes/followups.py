"""
Flixora AI Sales Automation Agent — Follow-Up Routes
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required

from app.extensions import db
from app.models import FollowUp
from app.services.followup_service import process_followups_cron

followups_bp = Blueprint('followups', __name__, url_prefix='/followups')


@followups_bp.route('')
@login_required
def index():
    """List all scheduled and processed follow-ups (§49)."""
    followups = FollowUp.query.order_by(FollowUp.scheduled_at.desc()).all()
    return render_template('followups/index.html',
                           followups=followups)


@followups_bp.route('/trigger-cron', methods=['POST'])
@login_required
def trigger_cron():
    """API endpoint to manually trigger follow-ups execution cron logic (§50)."""
    try:
        res = process_followups_cron()
        if res.get('success'):
            return jsonify({
                "success": True,
                "processed": res.get("processed"),
                "cancelled": res.get("cancelled"),
                "message": f"Cron execution complete. Processed: {res.get('processed')}, Cancelled: {res.get('cancelled')}."
            })
        else:
            return jsonify({"success": False, "error": "Cron failed."}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@followups_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_followup(id):
    """Delete a follow-up record securely."""
    fup = FollowUp.query.get_or_404(id)
    business_name = fup.lead.business_name if fup.lead else "Unknown"
    try:
        db.session.delete(fup)
        db.session.commit()
        flash(f"Follow-up for '{business_name}' has been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting follow-up: {str(e)}", "error")
    return redirect(url_for('followups.index'))
