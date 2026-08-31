"""
Flixora AI Sales Automation Agent — Demo Project Model

Explicit Lead ↔ Demo mapping (§37). Never depends solely on URL parsing.
"""
from datetime import datetime, timezone
from app.extensions import db


class DemoProject(db.Model):
    """Demo website project linked to a lead."""
    __tablename__ = 'demo_projects'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)

    demo_name = db.Column(db.String(200), nullable=False)
    demo_url = db.Column(db.String(500), nullable=False)
    business_name = db.Column(db.String(300), default='')
    notes = db.Column(db.Text, default='')

    # Validation (§38)
    url_valid = db.Column(db.Boolean, default=None)
    url_reachable = db.Column(db.Boolean, default=None)
    last_validated = db.Column(db.DateTime(timezone=True))

    # Status
    is_archived = db.Column(db.Boolean, default=False)
    publish_error = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<DemoProject {self.demo_name} → Lead {self.lead_id}>'
