"""
Flixora AI Sales Automation Agent — Pricing & Discount Models
"""
from datetime import datetime, timezone
from app.extensions import db


class PricingPlan(db.Model):
    """Pricing plans (Basic, Standard, Advanced, etc.)."""
    __tablename__ = 'pricing_plans'

    id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(100), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    features = db.Column(db.JSON, default=None)  # List of feature strings
    maintenance_price = db.Column(db.Float, default=0)
    is_enabled = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<PricingPlan {self.plan_name} ₹{self.price}>'


class DiscountRule(db.Model):
    """Discount rules with boundaries (§54)."""
    __tablename__ = 'discount_rules'

    id = db.Column(db.Integer, primary_key=True)
    pricing_plan_id = db.Column(db.Integer, db.ForeignKey('pricing_plans.id'), default=None)

    name = db.Column(db.String(100), nullable=False)
    normal_price = db.Column(db.Float, nullable=False)
    max_discount_percent = db.Column(db.Float, default=0)
    min_allowed_price = db.Column(db.Float, nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<DiscountRule {self.name} max={self.max_discount_percent}%>'
