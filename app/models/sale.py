"""
Flixora AI Sales Automation Agent — Sales Deal Model
"""
from datetime import datetime, timezone
from app.extensions import db
from app.constants import PipelineStage


class SalesDeal(db.Model):
    """Sales deal tracking through the pipeline."""
    __tablename__ = 'sales_deals'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)
    prd_id = db.Column(db.Integer, db.ForeignKey('prds.id'), default=None)
    demo_id = db.Column(db.Integer, db.ForeignKey('demo_projects.id'), default=None)
    pricing_plan_id = db.Column(db.Integer, db.ForeignKey('pricing_plans.id'), default=None)

    stage = db.Column(db.String(30), default=PipelineStage.NEW, index=True)
    deal_value = db.Column(db.Float, default=0)
    discount_applied = db.Column(db.Float, default=0)
    final_price = db.Column(db.Float, default=0)

    # Domain / Hosting / Maintenance (§56)
    domain_included = db.Column(db.Boolean, default=False)
    hosting_included = db.Column(db.Boolean, default=False)
    maintenance_included = db.Column(db.Boolean, default=False)

    notes = db.Column(db.Text, default='')
    won_at = db.Column(db.DateTime(timezone=True))
    lost_at = db.Column(db.DateTime(timezone=True))
    lost_reason = db.Column(db.String(500), default='')

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    events = db.relationship('SalesEvent', backref='deal', lazy='dynamic',
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<SalesDeal lead={self.lead_id} stage={self.stage}>'


class SalesEvent(db.Model):
    """Sales pipeline event tracking."""
    __tablename__ = 'sales_events'

    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('sales_deals.id'), nullable=False, index=True)

    event_type = db.Column(db.String(50), nullable=False)
    from_stage = db.Column(db.String(30), default='')
    to_stage = db.Column(db.String(30), default='')
    details = db.Column(db.Text, default='')
    occurred_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<SalesEvent {self.event_type}>'
