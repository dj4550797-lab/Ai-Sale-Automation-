"""
Flixora AI Sales Automation Agent — Message Model
"""
from datetime import datetime, timezone
from app.extensions import db


class Message(db.Model):
    """Individual message within a conversation."""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False, index=True)

    sender_type = db.Column(db.String(20), nullable=False)  # client, ai, admin
    sender_name = db.Column(db.String(100), default='')
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(30), default='text')  # text, image, document, system

    # Delivery tracking
    external_id = db.Column(db.String(200), default='')
    status = db.Column(db.String(30), default='sent')  # sent, delivered, read, failed

    # Classifications (§15)
    detected_intent = db.Column(db.String(100), default='')
    confidence = db.Column(db.Float, default=0.0)
    sales_stage = db.Column(db.String(50), default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Message {self.sender_type} in conv={self.conversation_id}>'
