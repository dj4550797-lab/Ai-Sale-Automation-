"""
Flixora AI Sales Automation Agent — Analytics Routes
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.extensions import db
from app.models import Lead, SalesDeal, LLMProvider, LLMModel
from app.constants import LeadStatus, PipelineStage

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('')
@login_required
def index():
    """Render the Analytics reports and metrics workspace."""
    # Lead stats
    total_leads = Lead.query.count()
    qualified = Lead.query.filter_by(status=LeadStatus.QUALIFIED).count()
    disqualified = Lead.query.filter_by(status=LeadStatus.DISQUALIFIED).count()
    interested = Lead.query.filter_by(status=LeadStatus.INTERESTED).count()
    contacted = Lead.query.filter_by(status=LeadStatus.CONTACTED).count()

    # Sales revenue
    deals = SalesDeal.query.all()
    revenue_won = sum(d.final_price for d in deals if d.stage == PipelineStage.WON)
    pipeline_value = sum(d.deal_value for d in deals if d.stage not in [PipelineStage.WON, PipelineStage.LOST])

    # LLM Metrics
    providers = LLMProvider.query.all()
    total_requests = sum(p.request_count or 0 for p in providers)
    total_failures = sum(p.failure_count or 0 for p in providers)
    total_fallbacks = sum(p.fallback_count or 0 for p in providers)
    
    success_rate = 100.0
    if total_requests > 0:
        success_rate = ((total_requests - total_failures) / total_requests) * 100.0

    return render_template('analytics/index.html',
                           total_leads=total_leads,
                           qualified=qualified,
                           disqualified=disqualified,
                           interested=interested,
                           contacted=contacted,
                           revenue_won=revenue_won,
                           pipeline_value=pipeline_value,
                           total_requests=total_requests,
                           success_rate=round(success_rate, 1),
                           total_fallbacks=total_fallbacks,
                           providers=providers)
