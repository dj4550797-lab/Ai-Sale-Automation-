"""
Flixora AI Sales Automation Agent — Automation Job Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import AutomationJobStatus


class AutomationJob(db.Model):
    """Automation job definition."""
    __tablename__ = 'automation_jobs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, default='')
    job_type = db.Column(db.String(50), nullable=False)  # lead_discovery, analysis, etc.
    cron_expression = db.Column(db.String(50), default='')
    status = db.Column(db.String(30), default=AutomationJobStatus.DISABLED, index=True)
    is_enabled = db.Column(db.Boolean, default=False)

    last_run_at = db.Column(db.DateTime(timezone=True))
    next_run_at = db.Column(db.DateTime(timezone=True))
    last_success_at = db.Column(db.DateTime(timezone=True))
    last_failure_at = db.Column(db.DateTime(timezone=True))
    last_error = db.Column(db.Text, default='')

    run_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)

    config = db.Column(db.JSON, default=None)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    runs = db.relationship('AutomationRun', backref='job', lazy='dynamic',
                           cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AutomationJob {self.name} [{self.status}]>'
