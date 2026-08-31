"""
Flixora AI Sales Automation Agent — Uploaded File Model
"""
from datetime import datetime, timezone
from app.extensions import db


class UploadedFile(db.Model):
    """Uploaded file metadata."""
    __tablename__ = 'uploaded_files'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    original_filename = db.Column(db.String(300), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(20), default='')  # image, logo, document
    mime_type = db.Column(db.String(100), default='')
    file_size = db.Column(db.Integer, default=0)  # bytes

    # Optional project association
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), default=None)
    prd_id = db.Column(db.Integer, db.ForeignKey('prds.id'), default=None)

    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), default=None)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<UploadedFile {self.original_filename}>'
