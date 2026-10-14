"""
Flixora AI Sales Automation Agent — Follow-Up Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import FollowUpStatus


class FollowUp(db.Model):
    """Scheduled follow-up for a lead."""
    __tablename__ = 'followups'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)
    outreach_id = db.Column(db.Integer, db.ForeignKey('outreach_campaigns.id'), default=None)

    followup_number = db.Column(db.Integer, default=1)
    channel = db.Column(db.String(30), default='')
    message_content = db.Column(db.Text, default='')
    status = db.Column(db.String(30), default=FollowUpStatus.SCHEDULED, index=True)

    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True))

    # Stop conditions (§51)
    stop_reason = db.Column(db.String(200), default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<FollowUp #{self.followup_number} lead={self.lead_id}>'
