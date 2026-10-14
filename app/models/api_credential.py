"""
Flixora AI Sales Automation Agent — API Credential Model

Credentials are encrypted before storage (§17-18).
The original secret is never shown again after initial save.
"""
from datetime import datetime, timezone
from app.extensions import db


class APICredential(db.Model):
    """Encrypted API credential linked to a provider."""
    __tablename__ = 'api_credentials'

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('llm_providers.id'), default=None, index=True)

    credential_type = db.Column(db.String(50), nullable=False)  # api_key, oauth_token, etc.
    service_name = db.Column(db.String(100), default='')  # google_maps, openrouter, etc.
    encrypted_value = db.Column(db.Text, nullable=False)  # Fernet-encrypted
    last_four = db.Column(db.String(10), default='')  # Last 4 chars for display

    is_valid = db.Column(db.Boolean, default=None)
    last_tested_at = db.Column(db.DateTime(timezone=True))
    last_error = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<APICredential {self.service_name} ••••{self.last_four}>'
