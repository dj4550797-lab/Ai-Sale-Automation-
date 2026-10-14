"""
Flixora AI Sales Automation Agent — Lead Model

Each field is stored independently per PRD §21.
"""
from datetime import datetime, timezone

from app.extensions import db
from app.constants import LeadStatus, LeadPriority


class Lead(db.Model):
    """Core lead / business record."""
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)

    # Business identity — separated fields (§21)
    business_name = db.Column(db.String(300), nullable=False, index=True)
    business_category = db.Column(db.String(100), default='', index=True)
    description = db.Column(db.Text, default='')
    address = db.Column(db.String(500), default='')
    city = db.Column(db.String(100), default='', index=True)
    state = db.Column(db.String(100), default='')
    country = db.Column(db.String(100), default='')
    postal_code = db.Column(db.String(20), default='')

    # Website
    website_url = db.Column(db.String(500), default='')
    website_exists = db.Column(db.Boolean, default=None)

    # Reputation
    rating = db.Column(db.Float, default=None)
    review_count = db.Column(db.Integer, default=0)

    # Qualification
    lead_score = db.Column(db.Integer, default=0, index=True)
    priority = db.Column(db.String(20), default=LeadPriority.MEDIUM)

    # Status & Pipeline
    status = db.Column(db.String(30), default=LeadStatus.NEW, index=True)

    # Google Places identity (§22 — preferred duplicate identity)
    google_place_id = db.Column(db.String(300), unique=True, default=None, index=True)
    business_hours = db.Column(db.String(500), default='')

    # Metadata
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    last_action = db.Column(db.String(200), default='')
    last_action_at = db.Column(db.DateTime(timezone=True))

    # Relationships
    contacts = db.relationship('LeadContact', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    social_profiles = db.relationship('SocialProfile', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    sources = db.relationship('LeadSource', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    website_analyses = db.relationship('WebsiteAnalysis', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    qualifications = db.relationship('LeadQualification', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    prds = db.relationship('PRD', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    demos = db.relationship('DemoProject', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    outreach_campaigns = db.relationship('OutreachCampaign', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    followups = db.relationship('FollowUp', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    sales_deals = db.relationship('SalesDeal', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    uploaded_files = db.relationship('UploadedFile', backref='lead', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Lead {self.business_name}>'
