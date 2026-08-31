"""
Flixora AI Sales Automation Agent — Social Profile Model
"""
from datetime import datetime, timezone
from app.extensions import db


class SocialProfile(db.Model):
    """Social media profiles linked to a lead."""
    __tablename__ = 'lead_social_profiles'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)

    platform = db.Column(db.String(50), nullable=False)  # instagram, facebook, etc.
    profile_url = db.Column(db.String(500), default='')
    username = db.Column(db.String(200), default='')
    follower_count = db.Column(db.Integer, default=None)
    is_verified = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<SocialProfile {self.platform}: {self.username}>'
