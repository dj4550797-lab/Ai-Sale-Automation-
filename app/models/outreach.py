"""
Flixora AI Sales Automation Agent — Outreach Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import OutreachStatus


class OutreachCampaign(db.Model):
    """Outreach campaign for a lead."""
    __tablename__ = 'outreach_campaigns'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)
    demo_id = db.Column(db.Integer, db.ForeignKey('demo_projects.id'), default=None)

    channel = db.Column(db.String(30), nullable=False)  # whatsapp, instagram, email
    message_content = db.Column(db.Text, default='')
    status = db.Column(db.String(30), default=OutreachStatus.READY, index=True)

    scheduled_at = db.Column(db.DateTime(timezone=True))
    sent_at = db.Column(db.DateTime(timezone=True))
    delivered_at = db.Column(db.DateTime(timezone=True))
    replied_at = db.Column(db.DateTime(timezone=True))

    error_message = db.Column(db.Text, default='')
    retry_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    events = db.relationship('OutreachEvent', backref='campaign', lazy='dynamic',
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<OutreachCampaign lead={self.lead_id} status={self.status}>'


class OutreachEvent(db.Model):
    """Individual outreach event tracking."""
    __tablename__ = 'outreach_events'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('outreach_campaigns.id'), nullable=False, index=True)

    event_type = db.Column(db.String(50), nullable=False)  # sent, delivered, opened, replied, failed
    details = db.Column(db.Text, default='')
    occurred_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<OutreachEvent {self.event_type}>'
