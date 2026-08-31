"""
Flixora AI Sales Automation Agent — Sales Pipeline Tests
"""
import pytest
from app import create_app
from app.extensions import db
from app.models import Lead, SalesDeal, SalesEvent
from app.constants import PipelineStage, LeadStatus
from app.services.auth_service import create_admin_user
from app.services.sales_service import get_deals_by_stage, update_deal_stage


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        create_admin_user(username='testadmin', email='test@flixora.com', password='password')
        yield app
        db.session.remove()
        db.drop_all()


def test_get_deals_by_stage(app):
    """Test retrieving deals grouped by kanban stages."""
    with app.app_context():
        lead = Lead(business_name="Delhi Diner", business_category="restaurant")
        db.session.add(lead)
        db.session.commit()

        deal = SalesDeal(lead_id=lead.id, stage=PipelineStage.CONTACTED)
        db.session.add(deal)
        db.session.commit()

        stages_map = get_deals_by_stage()
        assert len(stages_map[PipelineStage.CONTACTED]) == 1
        assert len(stages_map[PipelineStage.WON]) == 0


def test_transition_deal_stage_and_sync_lead(app):
    """Test transitioning deal stage updates lead status and registers history events."""
    with app.app_context():
        lead = Lead(business_name="Delhi Diner", business_category="restaurant", status=LeadStatus.CONTACTED)
        db.session.add(lead)
        db.session.commit()

        deal = SalesDeal(lead_id=lead.id, stage=PipelineStage.CONTACTED, deal_value=299.0)
        db.session.add(deal)
        db.session.commit()

        # Transition to Negotiation with updated value
        res = update_deal_stage(deal.id, PipelineStage.NEGOTIATION, deal_value=350.0)
        assert res['success'] is True
        assert res['stage'] == PipelineStage.NEGOTIATION

        # Verify deal sync
        db.session.refresh(deal)
        assert deal.stage == PipelineStage.NEGOTIATION
        assert deal.deal_value == 350.0
        assert deal.final_price == 350.0

        # Verify lead sync
        db.session.refresh(lead)
        assert lead.status == LeadStatus.NEGOTIATION

        # Verify event logging
        evt = SalesEvent.query.filter_by(deal_id=deal.id).first()
        assert evt is not None
        assert evt.from_stage == PipelineStage.CONTACTED
        assert evt.to_stage == PipelineStage.NEGOTIATION


def test_decline_deal_lost_state(app):
    """Test declining deal sets lost attributes and lost reason."""
    with app.app_context():
        lead = Lead(business_name="Delhi Diner", business_category="restaurant", status=LeadStatus.CONTACTED)
        db.session.add(lead)
        db.session.commit()

        deal = SalesDeal(lead_id=lead.id, stage=PipelineStage.CONTACTED)
        db.session.add(deal)
        db.session.commit()

        res = update_deal_stage(deal.id, PipelineStage.LOST, lost_reason="Budget too small")
        assert res['success'] is True

        db.session.refresh(deal)
        assert deal.stage == PipelineStage.LOST
        assert deal.lost_reason == "Budget too small"
        assert deal.lost_at is not None

        db.session.refresh(lead)
        assert lead.status == LeadStatus.LOST
