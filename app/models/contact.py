"""
Flixora AI Sales Automation Agent — Contact Model

Separate contact information from the lead record (§21).
"""
from datetime import datetime, timezone

from app.extensions import db


class LeadContact(db.Model):
    """Contact information linked to a lead."""
    __tablename__ = 'lead_contacts'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)

    contact_type = db.Column(db.String(30), nullable=False)  # phone, whatsapp, email
    value = db.Column(db.String(300), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    notes = db.Column(db.String(500), default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<LeadContact {self.contact_type}: {self.value}>'
