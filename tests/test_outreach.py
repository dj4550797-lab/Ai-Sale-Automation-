"""
Flixora AI Sales Automation Agent — Outreach Campaign Tests
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import Lead, PRD, DemoProject, OutreachCampaign, OutreachEvent, SalesDeal
from app.constants import OutreachStatus, LeadStatus, PipelineStage
from app.services.auth_service import create_admin_user
from app.services.outreach_service import (
    generate_outreach_message, create_outreach_campaign, send_outreach_campaign, simulate_incoming_reply
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        create_admin_user(username='testadmin', email='test@flixora.com', password='password')
        yield app
        db.session.remove()
        db.drop_all()


def test_outreach_message_generation(app):
    """Test generating outreach pitch compiles PRD goals and demo links."""
    with app.app_context():
        lead = Lead(business_name="Connaught Salon", business_category="salon")
        db.session.add(lead)
        db.session.commit()

        # Seed relations
        prd = PRD(lead_id=lead.id, status='approved', title="Concept Sitemap", website_goal="Attract brides")
        demo = DemoProject(lead_id=lead.id, demo_name="Concept Site", demo_url="http://mock-preview.com")
        db.session.add_all([prd, demo])
        db.session.commit()

        mock_pitch = "👋 Hello Connaught Salon! Check this demo: http://mock-preview.com to attract brides."
        with patch('app.services.outreach_service.llm_router.generate_text', return_value=mock_pitch):
            res = generate_outreach_message(lead.id, 'whatsapp')
            assert res['success'] is True
            assert "mock-preview.com" in res['message']


def test_send_outreach_campaign_simulated(app):
    """Test sending outreach triggers event tracking and logs contacted deal stages."""
    with app.app_context():
        lead = Lead(business_name="Connaught Salon", business_category="salon")
        db.session.add(lead)
        db.session.commit()

        # Seed outreach campaign
        camp = OutreachCampaign(lead_id=lead.id, channel='email', message_content="Pitch text", status=OutreachStatus.READY)
        db.session.add(camp)
        db.session.commit()

        res = send_outreach_campaign(camp.id)
        assert res['success'] is True
        assert res['status'] == OutreachStatus.DELIVERED  # delivered under test mode

        # Verify DB changes
        db.session.refresh(camp)
        assert camp.sent_at is not None
        assert camp.status == OutreachStatus.DELIVERED
        
        # Verify event logging
        evt_count = OutreachEvent.query.filter_by(campaign_id=camp.id).count()
        assert evt_count == 2 # sent + delivered

        # Verify Sales Deal is synchronized
        deal = SalesDeal.query.filter_by(lead_id=lead.id).first()
        assert deal is not None
        assert deal.stage == PipelineStage.CONTACTED
        assert lead.status == LeadStatus.CONTACTED


def test_simulate_incoming_reply_and_sentiment(app):
    """TestSimulate reply handles sentiment checks and stops follow-ups."""
    with app.app_context():
        lead = Lead(business_name="Connaught Salon", business_category="salon", status=LeadStatus.CONTACTED)
        db.session.add(lead)
        db.session.commit()

        deal = SalesDeal(lead_id=lead.id, stage=PipelineStage.CONTACTED)
        db.session.add(deal)
        db.session.commit()

        # Positive reply -> INTERESTED
        res = simulate_incoming_reply(lead.id, "Yes, how much is it?")
        assert res['success'] is True
        assert res['lead_status'] == LeadStatus.INTERESTED

        db.session.refresh(deal)
        assert deal.stage == PipelineStage.INTERESTED
