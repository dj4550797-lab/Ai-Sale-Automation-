"""
Flixora AI Sales Automation Agent — Automation Run Model
"""
from datetime import datetime, timezone
from app.extensions import db


class AutomationRun(db.Model):
    """Individual automation run record."""
    __tablename__ = 'automation_runs'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('automation_jobs.id'), nullable=False, index=True)

    # Lock key for duplicate prevention (§82)
    lock_key = db.Column(db.String(200), unique=True, default='')

    status = db.Column(db.String(30), default='running')  # running, completed, failed, cancelled
    started_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime(timezone=True))

    items_processed = db.Column(db.Integer, default=0)
    items_succeeded = db.Column(db.Integer, default=0)
    items_failed = db.Column(db.Integer, default=0)

    error_message = db.Column(db.Text, default='')
    log_output = db.Column(db.Text, default='')

    def __repr__(self):
        return f'<AutomationRun job={self.job_id} [{self.status}]>'
