"""
Flixora AI Sales Automation Agent — Knowledge Base Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import KBCategory


class KnowledgeBase(db.Model):
    """Knowledge base entries organized by category (§73)."""
    __tablename__ = 'knowledge_base'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<KnowledgeBase [{self.category}] {self.title}>'
