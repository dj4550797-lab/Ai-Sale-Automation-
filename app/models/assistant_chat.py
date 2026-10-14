"""
Flixora AI Sales Automation Agent — Admin AI Assistant Chat Models

Persists Admin Assistant chat sessions, message history, auto-saving, and uploaded image attachments.
"""
from datetime import datetime, timezone
from app.extensions import db


class AssistantSession(db.Model):
    """Admin AI chat session thread."""
    __tablename__ = 'assistant_sessions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), default='New Conversation', nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    messages = db.relationship(
        'AssistantMessage',
        backref='session',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='AssistantMessage.created_at.asc()'
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "message_count": self.messages.count()
        }


class AssistantMessage(db.Model):
    """Individual message in an Assistant chat session."""
    __tablename__ = 'assistant_messages'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('assistant_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    sender = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(500), default=None)  # relative web path e.g. /uploads/assistant/...
    tool_called = db.Column(db.String(100), default=None)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "sender": self.sender,
            "content": self.content,
            "image_path": self.image_path,
            "tool_called": self.tool_called,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
