"""
Flixora AI Sales Automation Agent — Dashboard Routes (§11-12)
"""
from flask import Blueprint, render_template
from flask_login import login_required

from app.extensions import db
from app.models import (
    Lead, PRD, DemoProject, OutreachCampaign, Conversation,
    SalesDeal, Notification, AutomationJob, LLMProvider
)
from app.constants import (
    LeadStatus, PRDStatus, PipelineStage, OutreachStatus,
    ProviderStatus, AutomationJobStatus
)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('')
@login_required
def index():
    """Main dashboard with KPIs, funnel, activity, and system status."""
    try:
        # KPI counts
        today_leads = Lead.query.count()
        qualified_leads = Lead.query.filter_by(status=LeadStatus.QUALIFIED).count()
        prds_pending = PRD.query.filter_by(status=PRDStatus.UNDER_REVIEW).count()
        demos_ready = DemoProject.query.filter_by(is_archived=False).count()
        messages_sent = OutreachCampaign.query.filter_by(status=OutreachStatus.SENT).count()
        replies = OutreachCampaign.query.filter_by(status=OutreachStatus.REPLIED).count()
        interested = SalesDeal.query.filter_by(stage=PipelineStage.INTERESTED).count()
        negotiations = SalesDeal.query.filter_by(stage=PipelineStage.NEGOTIATION).count()
        deals_won = SalesDeal.query.filter_by(stage=PipelineStage.WON).count()

        # Lead funnel data
        funnel = {
            'total': today_leads,
            'qualified': qualified_leads,
            'contacted': Lead.query.filter_by(status=LeadStatus.CONTACTED).count(),
            'replied': Lead.query.filter_by(status=LeadStatus.REPLIED).count(),
            'interested': Lead.query.filter_by(status=LeadStatus.INTERESTED).count(),
            'won': deals_won,
        }

        # Recent activity (last 10)
        recent_leads = Lead.query.order_by(Lead.updated_at.desc()).limit(10).all()

        # System status
        llm_healthy = LLMProvider.query.filter_by(status=ProviderStatus.HEALTHY).count()
        llm_total = LLMProvider.query.filter_by(is_enabled=True).count()
        automation_active = AutomationJob.query.filter_by(status=AutomationJobStatus.ACTIVE).count()

        # Notifications
        unread_count = Notification.query.filter_by(is_read=False).count()
    except Exception as e:
        db.session.rollback()
        today_leads = qualified_leads = prds_pending = demos_ready = messages_sent = replies = interested = negotiations = deals_won = 0
        funnel = {'total': 0, 'qualified': 0, 'contacted': 0, 'replied': 0, 'interested': 0, 'won': 0}
        recent_leads = []
        llm_healthy = llm_total = automation_active = unread_count = 0

    return render_template('dashboard/index.html',
        today_leads=today_leads,
        qualified_leads=qualified_leads,
        prds_pending=prds_pending,
        demos_ready=demos_ready,
        messages_sent=messages_sent,
        replies=replies,
        interested=interested,
        negotiations=negotiations,
        deals_won=deals_won,
        funnel=funnel,
        recent_leads=recent_leads,
        llm_healthy=llm_healthy,
        llm_total=llm_total,
        automation_active=automation_active,
        unread_count=unread_count,
    )


@dashboard_bp.route('/heartbeat')
@login_required
def heartbeat():
    """Global lightweight live-sync heartbeat to eliminate manual page reloads."""
    from flask import jsonify
    from flask_login import current_user
    from datetime import datetime, timezone, timedelta
    from app.models import Notification, Message, Conversation
    
    unread_notifs = 0
    if current_user and current_user.is_authenticated:
        unread_notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        
    # Check if a client message arrived in the last 25 seconds
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=25)
    latest_client_msg = Message.query.filter(
        Message.sender_type == 'client',
        Message.created_at >= cutoff
    ).order_by(Message.id.desc()).first()
    
    recent_msg_data = None
    if latest_client_msg:
        conv = Conversation.query.get(latest_client_msg.conversation_id)
        phone = conv.lead.primary_phone if (conv and conv.lead) else "Client"
        biz_name = conv.lead.business_name if (conv and conv.lead) else "WhatsApp Lead"
        recent_msg_data = {
            "id": latest_client_msg.id,
            "conversation_id": latest_client_msg.conversation_id,
            "sender": phone,
            "business_name": biz_name,
            "content": latest_client_msg.content[:90]
        }
        
    return jsonify({
        "success": True,
        "unread_notifications": unread_notifs,
        "recent_client_message": recent_msg_data
    })


@dashboard_bp.route('/stats')
@login_required
def live_stats():
    """Live KPI data endpoint for auto-updating dashboard widgets."""
    from flask import jsonify
    today_leads = Lead.query.count()
    qualified_leads = Lead.query.filter_by(status=LeadStatus.QUALIFIED).count()
    prds_pending = PRD.query.filter_by(status=PRDStatus.UNDER_REVIEW).count()
    demos_ready = DemoProject.query.filter_by(is_archived=False).count()
    messages_sent = OutreachCampaign.query.filter_by(status=OutreachStatus.SENT).count()
    replies = OutreachCampaign.query.filter_by(status=OutreachStatus.REPLIED).count()
    deals_won = SalesDeal.query.filter_by(stage=PipelineStage.WON).count()
    
    return jsonify({
        "success": True,
        "today_leads": today_leads,
        "qualified_leads": qualified_leads,
        "prds_pending": prds_pending,
        "demos_ready": demos_ready,
        "messages_sent": messages_sent,
        "replies": replies,
        "deals_won": deals_won
    })
