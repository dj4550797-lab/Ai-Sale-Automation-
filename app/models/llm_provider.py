"""
Flixora AI Sales Automation Agent — LLM Provider Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import ProviderStatus, LLMProtocol


class LLMProvider(db.Model):
    """LLM provider configuration."""
    __tablename__ = 'llm_providers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    protocol = db.Column(db.String(30), default=LLMProtocol.OPENAI_COMPATIBLE)
    base_url = db.Column(db.String(500), default='')
    status = db.Column(db.String(30), default=ProviderStatus.DISABLED, index=True)
    priority = db.Column(db.Integer, default=10)
    is_enabled = db.Column(db.Boolean, default=True)

    # Health tracking (§66)
    last_request_at = db.Column(db.DateTime(timezone=True))
    last_error_at = db.Column(db.DateTime(timezone=True))
    last_error_message = db.Column(db.Text, default='')
    request_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)
    fallback_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    models = db.relationship('LLMModel', backref='provider', lazy='dynamic',
                             cascade='all, delete-orphan')
    credentials = db.relationship('APICredential', backref='provider', lazy='dynamic',
                                  cascade='all, delete-orphan')

    @property
    def masked_key(self):
        cred = self.credentials.filter_by(credential_type='api_key').first()
        if cred and cred.last_four:
            return f"sk-••••••••••••{cred.last_four}"
        return "Not Configured"

    @property
    def default_model(self):
        from app.models.llm_model import LLMModel
        m = self.models.filter_by(is_enabled=True).order_by(LLMModel.priority.asc()).first()
        return m.display_name if m else "No Active Models"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'protocol': self.protocol,
            'base_url': self.base_url,
            'status': self.status,
            'priority': self.priority,
            'is_enabled': self.is_enabled,
            'masked_key': self.masked_key,
            'default_model': self.default_model
        }

    def __repr__(self):
        return f'<LLMProvider {self.name} [{self.status}]>'
