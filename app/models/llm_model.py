"""
Flixora AI Sales Automation Agent — LLM Model Configuration
"""
from datetime import datetime, timezone
from app.extensions import db


class LLMModel(db.Model):
    """Model configuration per provider."""
    __tablename__ = 'llm_models'

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('llm_providers.id'), nullable=False, index=True)

    model_id = db.Column(db.String(200), nullable=False)  # e.g. "google/gemini-pro"
    display_name = db.Column(db.String(200), default='')
    is_enabled = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=10)

    # Capabilities (§61)
    supports_text = db.Column(db.Boolean, default=True)
    supports_vision = db.Column(db.Boolean, default=False)
    supports_tool_calling = db.Column(db.Boolean, default=False)
    supports_structured_output = db.Column(db.Boolean, default=False)

    # Usage tracking
    last_used_at = db.Column(db.DateTime(timezone=True))
    total_requests = db.Column(db.Integer, default=0)
    total_failures = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'model_id': self.model_id,
            'display_name': self.display_name,
            'priority': self.priority,
            'is_enabled': self.is_enabled,
            'supports_text': self.supports_text,
            'supports_vision': self.supports_vision,
            'supports_tool_calling': self.supports_tool_calling,
            'supports_structured_output': self.supports_structured_output
        }

    def __repr__(self):
        return f'<LLMModel {self.display_name or self.model_id}>'
