"""
Flixora AI Sales Automation Agent — Outreach Campaign Routes
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Lead, OutreachCampaign, PRD, DemoProject
from app.services.outreach_service import (
    create_outreach_campaign, send_outreach_campaign, simulate_incoming_reply
)
from app.security.validation import sanitize_string

outreach_bp = Blueprint('outreach', __name__, url_prefix='/outreach')


@outreach_bp.route('')
@login_required
def index():
    """List all leads alongside their outreach states."""
    search_query = sanitize_string(request.args.get('search', ''))
    
    query = Lead.query
    if search_query:
        query = query.filter(Lead.business_name.ilike(f"%{search_query}%"))
        
    leads = query.order_by(Lead.business_name.asc()).all()
    
    lead_campaigns = []
    for lead in leads:
        prd = PRD.query.filter_by(lead_id=lead.id, status='approved').first()
        demo = DemoProject.query.filter_by(lead_id=lead.id).first()
        campaign = OutreachCampaign.query.filter_by(lead_id=lead.id).first()
        
        lead_campaigns.append({
            "lead": lead,
            "prd": prd,
            "demo": demo,
            "campaign": campaign
        })

    return render_template('outreach/index.html',
                           lead_campaigns=lead_campaigns)


@outreach_bp.route('/prepare/<int:lead_id>', methods=['POST'])
@login_required
def prepare(lead_id):
    """API endpoint to prepare/draft an outreach campaign and compile pitch text."""
    channel = sanitize_string(request.form.get('channel', 'email'))
    
    res = create_outreach_campaign(lead_id, channel)
    if res.get('success'):
        return jsonify({
            "success": True,
            "campaign_id": res.get("campaign_id"),
            "message": res.get("message"),
            "channel": channel
        })
    else:
        return jsonify({"success": False, "error": res.get("error")}), 400


@outreach_bp.route('/send/<int:campaign_id>', methods=['POST'])
@login_required
def send(campaign_id):
    """API endpoint to update pitch content and execute sending (§41)."""
    message_content = request.form.get('message_content', '')
    
    if not message_content:
        return jsonify({"success": False, "error": "Message content cannot be empty."}), 400

    campaign = OutreachCampaign.query.get_or_404(campaign_id)
    # Save the edited/final message
    campaign.message_content = message_content
    db.session.commit()

    res = send_outreach_campaign(campaign_id)
    if res.get('success'):
        return jsonify({
            "success": True,
            "status": res.get("status"),
            "message": "Message sent successfully."
        })
    else:
        return jsonify({"success": False, "error": res.get("error")}), 400


@outreach_bp.route('/simulate-reply/<int:lead_id>', methods=['POST'])
@login_required
def simulate_reply(lead_id):
    """API endpoint to mock incoming replies for validation testing."""
    reply_content = sanitize_string(request.form.get('reply', ''))
    
    if not reply_content:
        return jsonify({"success": False, "error": "Reply text cannot be empty."}), 400

    res = simulate_incoming_reply(lead_id, reply_content)
    if res.get('success'):
        return jsonify({
            "success": True,
            "lead_status": res.get("lead_status"),
            "message": "Reply registered successfully."
        })
    else:
        return jsonify({"success": False, "error": res.get("error")}), 400


@outreach_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_campaign(id):
    """Delete an outreach campaign securely."""
    campaign = OutreachCampaign.query.get_or_404(id)
    business_name = campaign.lead.business_name if campaign.lead else "Unknown"
    try:
        db.session.delete(campaign)
        db.session.commit()
        flash(f"Outreach campaign for '{business_name}' has been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting outreach campaign: {str(e)}", "error")
    return redirect(url_for('outreach.index'))
