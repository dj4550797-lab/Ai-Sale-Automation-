"""
Flixora AI Sales Automation Agent — Performance Event Model
"""
from datetime import datetime, timezone
from app.extensions import db


class PerformanceEvent(db.Model):
    """Performance tracking event with points (§85)."""
    __tablename__ = 'performance_events'

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    points = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, default='')

    # Related entity
    entity_type = db.Column(db.String(50), default='')  # lead, prd, outreach, etc.
    entity_id = db.Column(db.Integer, default=None)

    occurred_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<PerformanceEvent {self.event_type} {self.points:+d}>'
