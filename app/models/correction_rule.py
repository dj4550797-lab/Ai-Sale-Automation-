"""
Flixora AI Sales Automation Agent — Correction Rule Model
"""
from datetime import datetime, timezone
from app.extensions import db


class CorrectionRule(db.Model):
    """Error correction rules created from AI mistakes (§84-87)."""
    __tablename__ = 'correction_rules'

    id = db.Column(db.Integer, primary_key=True)
    error_type = db.Column(db.String(100), nullable=False, index=True)
    error_description = db.Column(db.Text, default='')
    cause = db.Column(db.Text, default='')
    correction = db.Column(db.Text, default='')

    # Escalation tracking (§87)
    occurrence_count = db.Column(db.Integer, default=1)
    requires_approval = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<CorrectionRule {self.error_type} x{self.occurrence_count}>'
