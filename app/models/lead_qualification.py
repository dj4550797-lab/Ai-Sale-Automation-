"""
Flixora AI Sales Automation Agent — Lead Qualification Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import LeadPriority


class LeadQualification(db.Model):
    """Lead qualification score and reasoning."""
    __tablename__ = 'lead_qualifications'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)

    score = db.Column(db.Integer, nullable=False, default=0)
    priority = db.Column(db.String(20), default=LeadPriority.MEDIUM)
    reason = db.Column(db.Text, default='')
    opportunity = db.Column(db.Text, default='')
    website_status = db.Column(db.String(50), default='')
    recommended_action = db.Column(db.String(200), default='')
    confidence = db.Column(db.Float, default=None)

    # Evidence references (§121)
    evidence = db.Column(db.JSON, default=None)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<LeadQualification lead={self.lead_id} score={self.score}>'
