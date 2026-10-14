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
        'total': Lead.query.count(),
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
