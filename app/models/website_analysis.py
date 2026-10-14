"""
Flixora AI Sales Automation Agent — Website Analysis Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import WebsiteVerdict


class WebsiteAnalysis(db.Model):
    """Website analysis results with separated criteria (§26)."""
    __tablename__ = 'website_analysis'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)

    # Analysis target
    url = db.Column(db.String(500), default='')
    website_exists = db.Column(db.Boolean, default=False)

    # Separated analysis scores (§26)
    visual_design_score = db.Column(db.Integer, default=None)
    layout_score = db.Column(db.Integer, default=None)
    typography_score = db.Column(db.Integer, default=None)
    branding_score = db.Column(db.Integer, default=None)
    mobile_score = db.Column(db.Integer, default=None)
    navigation_score = db.Column(db.Integer, default=None)
    cta_score = db.Column(db.Integer, default=None)
    contact_flow_score = db.Column(db.Integer, default=None)
    service_presentation_score = db.Column(db.Integer, default=None)
    trust_signals_score = db.Column(db.Integer, default=None)
    performance_score = db.Column(db.Integer, default=None)
    accessibility_score = db.Column(db.Integer, default=None)
    conversion_score = db.Column(db.Integer, default=None)

    # Overall
    overall_score = db.Column(db.Integer, default=None)
    verdict = db.Column(db.String(30), default=WebsiteVerdict.NO_WEBSITE)
    improvement_needed = db.Column(db.Boolean, default=None)
    improvement_reason = db.Column(db.Text, default='')

    # Separated findings (§26 — observed fact vs AI recommendation vs inference)
    observed_facts = db.Column(db.JSON, default=None)
    ai_recommendations = db.Column(db.JSON, default=None)
    ai_inferences = db.Column(db.JSON, default=None)

    # Status
    status = db.Column(db.String(30), default='pending')  # pending, analyzing, completed, failed
    error_message = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime(timezone=True))

    def __repr__(self):
        return f'<WebsiteAnalysis lead={self.lead_id} score={self.overall_score}>'
