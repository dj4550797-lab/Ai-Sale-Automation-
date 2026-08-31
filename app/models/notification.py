"""
Flixora AI Sales Automation Agent — Notification Model
"""
from datetime import datetime, timezone
from app.extensions import db


class Notification(db.Model):
    """Admin notification record."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    message = db.Column(db.Text, default='')
    is_read = db.Column(db.Boolean, default=False, index=True)

    # Optional link to related entity
    entity_type = db.Column(db.String(50), default='')
    entity_id = db.Column(db.Integer, default=None)
    action_url = db.Column(db.String(500), default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    read_at = db.Column(db.DateTime(timezone=True))

    def __repr__(self):
        return f'<Notification {self.type}: {self.title}>'
