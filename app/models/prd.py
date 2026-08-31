"""
Flixora AI Sales Automation Agent — PRD Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import PRDStatus


class PRD(db.Model):
    """Product Requirements Document for a lead's website."""
    __tablename__ = 'prds'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)

    title = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(30), default=PRDStatus.DRAFT, index=True)
    current_version = db.Column(db.Integer, default=1)

    # PRD Content sections (§31)
    business_overview = db.Column(db.Text, default='')
    business_analysis = db.Column(db.Text, default='')
    website_goal = db.Column(db.Text, default='')
    target_audience = db.Column(db.Text, default='')
    design_direction = db.Column(db.Text, default='')
    site_structure = db.Column(db.Text, default='')
    functional_requirements = db.Column(db.Text, default='')
    content_requirements = db.Column(db.Text, default='')
    cta_strategy = db.Column(db.Text, default='')
    technical_requirements = db.Column(db.Text, default='')

    # Context
    is_improvement = db.Column(db.Boolean, default=False)  # True = existing website improvement
    improvement_reason = db.Column(db.Text, default='')

    # Metadata
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    approved_at = db.Column(db.DateTime(timezone=True))
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    versions = db.relationship('PRDVersion', backref='prd', lazy='dynamic',
                               cascade='all, delete-orphan', order_by='PRDVersion.version.desc()')

    def __repr__(self):
        return f'<PRD {self.title} v{self.current_version}>'
