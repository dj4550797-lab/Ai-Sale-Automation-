"""
Flixora AI Sales Automation Agent — Lead Source Model
"""
from datetime import datetime, timezone
from app.extensions import db


class LeadSource(db.Model):
    """Tracks the source/origin of a lead discovery."""
    __tablename__ = 'lead_sources'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)

    source_type = db.Column(db.String(50), nullable=False)  # google_places, manual, import
    source_query = db.Column(db.String(300), default='')  # e.g., "salon delhi"
    source_location = db.Column(db.String(200), default='')
    source_category = db.Column(db.String(100), default='')
    raw_data = db.Column(db.JSON, default=None)  # Original API response (non-secret parts)
    discovered_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<LeadSource {self.source_type} for lead {self.lead_id}>'
