"""
Flixora AI Sales Automation Agent — Activity Log Model

Audit trail for important actions (§116).
"""
from datetime import datetime, timezone
from app.extensions import db


class ActivityLog(db.Model):
    """Audit trail record."""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), default=None, index=True)
    actor_type = db.Column(db.String(20), default='admin')  # admin, ai, system

    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), default='', index=True)
    entity_id = db.Column(db.Integer, default=None)
    description = db.Column(db.Text, default='')

    # Before/After for auditing (§116)
    before_data = db.Column(db.JSON, default=None)
    after_data = db.Column(db.JSON, default=None)
    result = db.Column(db.String(30), default='success')  # success, failure, error

    ip_address = db.Column(db.String(45), default='')
    user_agent = db.Column(db.String(500), default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ActivityLog {self.action} on {self.entity_type}>'
