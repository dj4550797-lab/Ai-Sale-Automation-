"""
Flixora AI Sales Automation Agent — Settings Model
"""
from datetime import datetime, timezone

from app.extensions import db


class Setting(db.Model):
    """Key-value settings with category grouping."""
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    key = db.Column(db.String(100), nullable=False, index=True)
    value = db.Column(db.Text, default='')
    value_type = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    description = db.Column(db.String(500), default='')
    is_secret = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('category', 'key', name='uq_setting_category_key'),
    )

    def __repr__(self):
        return f'<Setting {self.category}.{self.key}>'
