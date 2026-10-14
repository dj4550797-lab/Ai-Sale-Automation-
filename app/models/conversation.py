"""
Flixora AI Sales Automation Agent — Conversation Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import ConversationStatus


class Conversation(db.Model):
    """Client conversation session with isolated context (§48)."""
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)

    status = db.Column(db.String(30), default=ConversationStatus.AI_ACTIVE, index=True)
    channel = db.Column(db.String(30), default='')  # whatsapp, instagram, email, internal
    subject = db.Column(db.String(300), default='')

    # Context isolation — each conversation has its own context
    context_data = db.Column(db.JSON, default=None)

    # Admin takeover (§45)
    taken_over_by = db.Column(db.Integer, db.ForeignKey('users.id'), default=None)
    taken_over_at = db.Column(db.DateTime(timezone=True))

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    closed_at = db.Column(db.DateTime(timezone=True))

    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy='dynamic',
                               cascade='all, delete-orphan', order_by='Message.created_at')

    def __repr__(self):
        return f'<Conversation lead={self.lead_id} status={self.status}>'
