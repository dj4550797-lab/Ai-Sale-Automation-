"""
Flixora AI Sales Automation Agent — PRD Version History Model
"""
from datetime import datetime, timezone
from app.extensions import db


class PRDVersion(db.Model):
    """Versioned snapshot of a PRD (§34)."""
    __tablename__ = 'prd_versions'

    id = db.Column(db.Integer, primary_key=True)
    prd_id = db.Column(db.Integer, db.ForeignKey('prds.id'), nullable=False, index=True)

    version = db.Column(db.Integer, nullable=False)
    author_type = db.Column(db.String(20), default='ai')  # ai, admin
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), default=None)
    change_summary = db.Column(db.Text, default='')

    # Full PRD content snapshot
    content_snapshot = db.Column(db.JSON, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('prd_id', 'version', name='uq_prd_version'),
    )

    def __repr__(self):
        return f'<PRDVersion prd={self.prd_id} v{self.version}>'
