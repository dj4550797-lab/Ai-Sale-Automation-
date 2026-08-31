"""
Flixora AI Sales Automation Agent — Deletion Operations and Cascade Tests
"""
import pytest
from app import create_app
from app.extensions import db
from app.models import (
    Lead, LeadContact, WebsiteAnalysis, PRD, PRDVersion,
    DemoProject, OutreachCampaign, FollowUp, Conversation,
    Message, SalesDeal, UploadedFile
)
from app.services.auth_service import create_admin_user


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Seed test admin
        create_admin_user(
            username='testadmin',
            email='testadmin@flixora.com',
            password='password123'
        )
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login_admin(client):
    client.post('/login', data={'username': 'testadmin', 'password': 'password123'})


def test_lead_delete_cascade(client, app):
    """Test that deleting a lead cleans up all owned child records and does not orphan them."""
    login_admin(client)

    with app.app_context():
        # Create Lead
        lead = Lead(business_name="Test Business to Delete", business_category="services")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

        # Add child records
        contact = LeadContact(lead_id=lead_id, contact_type="email", value="john@test.com")
        analysis = WebsiteAnalysis(lead_id=lead_id, status="completed", overall_score=85)
        prd = PRD(lead_id=lead_id, title="Test PRD Title")
        db.session.add_all([contact, analysis, prd])
        db.session.commit()

        # Add records dependent on PRD/Lead
        from datetime import datetime, timezone
        prd_ver = PRDVersion(prd_id=prd.id, version=1, content_snapshot={})
        demo = DemoProject(lead_id=lead_id, demo_name="Test Demo", demo_url="http://local.preview")
        campaign = OutreachCampaign(lead_id=lead_id, channel="email", status="ready")
        fup = FollowUp(lead_id=lead_id, followup_number=1, channel="email", scheduled_at=datetime.now(timezone.utc))
        conv = Conversation(lead_id=lead_id, channel="email")
        db.session.add_all([prd_ver, demo, campaign, fup, conv])
        db.session.commit()

        # Add message under Conversation, deal, and uploaded file
        msg = Message(conversation_id=conv.id, sender_type="client", content="Hello")
        deal = SalesDeal(lead_id=lead_id, deal_value=5000.0, stage="lead_inflow")
        up_file = UploadedFile(lead_id=lead_id, filename="test.pdf", original_filename="test.pdf", file_path="uploads/test.pdf")
        db.session.add_all([msg, deal, up_file])
        db.session.commit()

        # Store IDs for verification
        prd_id = prd.id
        conv_id = conv.id

        # Verify initial state
        assert Lead.query.get(lead_id) is not None
        assert LeadContact.query.get(contact.id) is not None
        assert WebsiteAnalysis.query.get(analysis.id) is not None
        assert PRD.query.get(prd_id) is not None
        assert PRDVersion.query.get(prd_ver.id) is not None
        assert DemoProject.query.get(demo.id) is not None
        assert OutreachCampaign.query.get(campaign.id) is not None
        assert FollowUp.query.get(fup.id) is not None
        assert Conversation.query.get(conv_id) is not None
        assert Message.query.get(msg.id) is not None
        assert SalesDeal.query.get(deal.id) is not None
        assert UploadedFile.query.get(up_file.id) is not None

        # Another lead to prove isolation
        other_lead = Lead(business_name="Safe Lead", business_category="tech")
        db.session.add(other_lead)
        db.session.commit()
        other_lead_id = other_lead.id

    # Execute deletion POST request
    response = client.post(f'/leads/{lead_id}/delete')
    assert response.status_code in [200, 302]

    # Verify everything cascade-deleted correctly
    with app.app_context():
        assert Lead.query.get(lead_id) is None
        assert LeadContact.query.filter_by(lead_id=lead_id).first() is None
        assert WebsiteAnalysis.query.filter_by(lead_id=lead_id).first() is None
        assert PRD.query.get(prd_id) is None
        assert PRDVersion.query.filter_by(prd_id=prd_id).first() is None
        assert DemoProject.query.filter_by(lead_id=lead_id).first() is None
        assert OutreachCampaign.query.filter_by(lead_id=lead_id).first() is None
        assert FollowUp.query.filter_by(lead_id=lead_id).first() is None
        assert Conversation.query.get(conv_id) is None
        assert Message.query.filter_by(conversation_id=conv_id).first() is None
        assert SalesDeal.query.filter_by(lead_id=lead_id).first() is None
        assert UploadedFile.query.filter_by(lead_id=lead_id).first() is None

        # Verify other lead is untouched
        assert Lead.query.get(other_lead_id) is not None


def test_prd_delete_isolation(client, app):
    """Test that deleting a PRD does not delete the Lead and cleans up PRD versions."""
    login_admin(client)

    with app.app_context():
        lead = Lead(business_name="Safe Lead PRD Test", business_category="retail")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

        prd = PRD(lead_id=lead_id, title="Test PRD to Delete")
        db.session.add(prd)
        db.session.commit()
        prd_id = prd.id

        prd_ver = PRDVersion(prd_id=prd_id, version=1, content_snapshot={})
        db.session.add(prd_ver)
        db.session.commit()
        prd_ver_id = prd_ver.id

    response = client.post(f'/prds/{prd_id}/delete')
    assert response.status_code in [200, 302]

    with app.app_context():
        assert PRD.query.get(prd_id) is None
        assert PRDVersion.query.get(prd_ver_id) is None
        assert Lead.query.get(lead_id) is not None


def test_demo_delete_isolation(client, app):
    """Test that deleting a demo project record does not delete the lead."""
    login_admin(client)

    with app.app_context():
        lead = Lead(business_name="Safe Lead Demo Test", business_category="cafes")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

        demo = DemoProject(lead_id=lead_id, demo_name="Test Demo to Delete", demo_url="http://localhost/demo")
        db.session.add(demo)
        db.session.commit()
        demo_id = demo.id

    response = client.post(f'/demos/{demo_id}/delete')
    assert response.status_code in [200, 302]

    with app.app_context():
        assert DemoProject.query.get(demo_id) is None
        assert Lead.query.get(lead_id) is not None


def test_analysis_delete_isolation(client, app):
    """Test that deleting a website analysis does not delete the lead."""
    login_admin(client)

    with app.app_context():
        lead = Lead(business_name="Safe Lead Analysis Test", business_category="gym")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

        analysis = WebsiteAnalysis(lead_id=lead_id, status="completed", overall_score=90)
        db.session.add(analysis)
        db.session.commit()
        analysis_id = analysis.id

    response = client.post(f'/analysis/{analysis_id}/delete')
    assert response.status_code in [200, 302]

    with app.app_context():
        assert WebsiteAnalysis.query.get(analysis_id) is None
        assert Lead.query.get(lead_id) is not None


def test_campaign_delete_isolation(client, app):
    """Test that deleting an outreach campaign does not delete the lead."""
    login_admin(client)

    with app.app_context():
        lead = Lead(business_name="Safe Lead Campaign Test", business_category="salons")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

        campaign = OutreachCampaign(lead_id=lead_id, channel="email", status="ready")
        db.session.add(campaign)
        db.session.commit()
        campaign_id = campaign.id

    response = client.post(f'/outreach/{campaign_id}/delete')
    assert response.status_code in [200, 302]

    with app.app_context():
        assert OutreachCampaign.query.get(campaign_id) is None
        assert Lead.query.get(lead_id) is not None


def test_followup_delete_isolation(client, app):
    """Test that deleting a scheduled followup does not delete the lead."""
    login_admin(client)

    with app.app_context():
        lead = Lead(business_name="Safe Lead Followup Test", business_category="bars")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

        from datetime import datetime, timezone
        fup = FollowUp(lead_id=lead_id, followup_number=2, channel="whatsapp", scheduled_at=datetime.now(timezone.utc))
        db.session.add(fup)
        db.session.commit()
        fup_id = fup.id

    response = client.post(f'/followups/{fup_id}/delete')
    assert response.status_code in [200, 302]

    with app.app_context():
        assert FollowUp.query.get(fup_id) is None
        assert Lead.query.get(lead_id) is not None


def test_conversation_delete_isolation(client, app):
    """Test that deleting a conversation does not delete the lead."""
    login_admin(client)

    with app.app_context():
        lead = Lead(business_name="Safe Lead Conversation Test", business_category="hotels")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

        conv = Conversation(lead_id=lead_id, channel="whatsapp")
        db.session.add(conv)
        db.session.commit()
        conv_id = conv.id

    response = client.post(f'/conversations/{conv_id}/delete')
    assert response.status_code in [200, 302]

    with app.app_context():
        assert Conversation.query.get(conv_id) is None
        assert Lead.query.get(lead_id) is not None


def test_sales_deal_delete_isolation(client, app):
    """Test that deleting a sales deal record does not delete the lead."""
    login_admin(client)

    with app.app_context():
        lead = Lead(business_name="Safe Lead Sales Deal Test", business_category="clinics")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

        deal = SalesDeal(lead_id=lead_id, deal_value=2500.0, stage="negotiation")
        db.session.add(deal)
        db.session.commit()
        deal_id = deal.id

    response = client.post(f'/sales/{deal_id}/delete')
    assert response.status_code in [200, 302]

    with app.app_context():
        assert SalesDeal.query.get(deal_id) is None
        assert Lead.query.get(lead_id) is not None


def test_deletion_security_constraints(client, app):
    """Test that unauthenticated users cannot delete records, and GET requests are blocked."""
    with app.app_context():
        lead = Lead(business_name="Security Test Business", business_category="security")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

    # 1. Unauthenticated POST should fail/redirect
    response = client.post(f'/leads/{lead_id}/delete')
    assert response.status_code in [302, 401]

    # Verify lead still exists
    with app.app_context():
        assert Lead.query.get(lead_id) is not None

    # 2. Authenticated GET request should be blocked / Method Not Allowed (405)
    login_admin(client)
    response_get = client.get(f'/leads/{lead_id}/delete')
    assert response_get.status_code == 405

    # Verify lead still exists
    with app.app_context():
        assert Lead.query.get(lead_id) is not None


def test_delete_multiple_leads(client, app):
    """Test bulk deletion of selected leads."""
    login_admin(client)

    with app.app_context():
        lead1 = Lead(business_name="Lead 1 to delete", business_category="a")
        lead2 = Lead(business_name="Lead 2 to delete", business_category="b")
        lead3 = Lead(business_name="Safe Lead", business_category="c")
        db.session.add_all([lead1, lead2, lead3])
        db.session.commit()
        
        lead1_id = lead1.id
        lead2_id = lead2.id
        lead3_id = lead3.id

    # 1. Post empty bulk delete
    response_empty = client.post('/leads/delete-multiple', data={})
    assert response_empty.status_code in [200, 302]
    
    # 2. Post valid bulk delete
    response = client.post('/leads/delete-multiple', data={'lead_ids[]': [lead1_id, lead2_id]})
    assert response.status_code in [200, 302]
    
    with app.app_context():
        assert Lead.query.get(lead1_id) is None
        assert Lead.query.get(lead2_id) is None
        assert Lead.query.get(lead3_id) is not None
