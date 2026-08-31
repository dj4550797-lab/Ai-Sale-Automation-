"""
Flixora AI Sales Automation Agent — Follow-Up Scheduler Tests
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models import Lead, PRD, DemoProject, OutreachCampaign, FollowUp, OutreachEvent
from app.constants import FollowUpStatus, LeadStatus, OutreachStatus
from app.services.auth_service import create_admin_user
from app.services.followup_service import schedule_next_followup, process_followups_cron


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        create_admin_user(username='testadmin', email='test@flixora.com', password='password')
        yield app
        db.session.remove()
        db.drop_all()


def test_schedule_followup(app):
    """Test scheduling followup creates DB record with target delay date."""
    with app.app_context():
        lead = Lead(business_name="Delhi Diner", business_category="restaurant")
        db.session.add(lead)
        db.session.commit()

        camp = OutreachCampaign(lead_id=lead.id, channel='whatsapp', status=OutreachStatus.SENT)
        db.session.add(camp)
        db.session.commit()

        res = schedule_next_followup(lead.id, camp.id, followup_number=1, delay_days=2)
        assert res['success'] is True

        fup = FollowUp.query.get(res['followup_id'])
        assert fup is not None
        assert fup.followup_number == 1
        assert fup.status == FollowUpStatus.SCHEDULED
        
        # Verify scheduled time is approx 2 days from now
        diff = fup.scheduled_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
        assert diff.days == 1 or diff.days == 2  # due to timezone/microsecond boundaries


def test_cron_executes_followup_and_reschedules(app):
    """Test cron scans due followups, compiles text, sends, and schedules next follow-up."""
    with app.app_context():
        lead = Lead(business_name="Delhi Diner", business_category="restaurant", status=LeadStatus.CONTACTED)
        db.session.add(lead)
        db.session.commit()

        demo = DemoProject(lead_id=lead.id, demo_name="Concept", demo_url="http://diner.com")
        db.session.add(demo)
        db.session.commit()

        camp = OutreachCampaign(lead_id=lead.id, demo_id=demo.id, channel='whatsapp', status=OutreachStatus.SENT)
        db.session.add(camp)
        db.session.commit()

        # Seed scheduled followup due in past
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        fup = FollowUp(
            lead_id=lead.id,
            outreach_id=camp.id,
            followup_number=1,
            channel='whatsapp',
            status=FollowUpStatus.SCHEDULED,
            scheduled_at=past_time
        )
        db.session.add(fup)
        db.session.commit()

        mock_followup = "Hi, checking if you saw our concept preview."

        with patch('app.services.followup_service.llm_router.generate_text', return_value=mock_followup):
            cron_res = process_followups_cron()
            assert cron_res['processed'] == 1
            assert cron_res['cancelled'] == 0

            # Verify fup status
            db.session.refresh(fup)
            assert fup.status == FollowUpStatus.SENT
            assert fup.message_content == mock_followup

            # Verify next follow-up scheduled
            next_fup = FollowUp.query.filter_by(lead_id=lead.id, followup_number=2).first()
            assert next_fup is not None
            assert next_fup.status == FollowUpStatus.SCHEDULED


def test_stop_conditions_met(app):
    """Test stop conditions cancel followups and write stop reasons (§51)."""
    with app.app_context():
        # Setup lead that replied
        lead = Lead(business_name="Delhi Diner", business_category="restaurant", status=LeadStatus.REPLIED)
        db.session.add(lead)
        db.session.commit()

        camp = OutreachCampaign(lead_id=lead.id, channel='whatsapp', status=OutreachStatus.REPLIED)
        db.session.add(camp)
        db.session.commit()

        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        fup = FollowUp(
            lead_id=lead.id,
            outreach_id=camp.id,
            followup_number=1,
            channel='whatsapp',
            status=FollowUpStatus.SCHEDULED,
            scheduled_at=past_time
        )
        db.session.add(fup)
        db.session.commit()

        cron_res = process_followups_cron()
        assert cron_res['processed'] == 0
        assert cron_res['cancelled'] == 1

        db.session.refresh(fup)
        assert fup.status == FollowUpStatus.CANCELLED
        assert "Stop condition met" in fup.stop_reason
