"""
Flixora AI Sales Automation Agent — PRD Generation and Revision Tests
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import Lead, WebsiteAnalysis, PRD, PRDVersion
from app.constants import PRDStatus, LeadStatus, WebsiteVerdict
from app.services.auth_service import create_admin_user
from app.services.prd_service import generate_lead_prd, revise_prd_with_ai


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        create_admin_user(username='testadmin', email='test@flixora.com', password='password')
        yield app
        db.session.remove()
        db.drop_all()


def test_generate_new_website_prd(app):
    """Test generating a PRD for a lead with no existing website."""
    with app.app_context():
        lead = Lead(business_name="Desert Bakery", business_category="bakery", website_url="")
        db.session.add(lead)
        db.session.commit()

        mock_prd_response = {
            "title": "Flixora Website PRD - Desert Bakery",
            "business_overview": "Desert Bakery is a local bakery in Delhi.",
            "business_analysis": "No existing online footprint.",
            "website_goal": "Establish online presence, order cakes online.",
            "target_audience": "Local sweet tooths, wedding event planners.",
            "design_direction": "Warm pastel colors, friendly script typography.",
            "site_structure": "Home, Menu, Custom Orders, Gallery, Contact.",
            "functional_requirements": "Order configuration form, WhatsApp redirection.",
            "content_requirements": "Product photos, ingredients lists, owner story.",
            "cta_strategy": "Header 'Order Now' button, inline custom order buttons.",
            "technical_requirements": "Fast hosting, Google Analytics, responsive layout."
        }

        with patch('app.services.prd_service.llm_router.generate_structured_output', return_value=mock_prd_response):
            res = generate_lead_prd(lead.id)
            assert res['success'] is True
            assert res['version'] == 1

            prd = PRD.query.filter_by(lead_id=lead.id).first()
            assert prd is not None
            assert prd.title == "Flixora Website PRD - Desert Bakery"
            assert prd.status == PRDStatus.READY
            assert prd.is_improvement is False
            assert lead.status == LeadStatus.RESEARCHED

            # Check version details
            version = PRDVersion.query.filter_by(prd_id=prd.id, version=1).first()
            assert version is not None
            assert version.author_type == 'ai'
            assert version.content_snapshot['website_goal'] == "Establish online presence, order cakes online."


def test_prd_adequate_website_skipped(app):
    """Test that PRD is not generated if existing website is adequate."""
    with app.app_context():
        lead = Lead(business_name="Super Dental", business_category="dentist", website_url="http://superdental.com")
        db.session.add(lead)
        db.session.commit()

        # Seed adequate analysis
        analysis = WebsiteAnalysis(
            lead_id=lead.id,
            url=lead.website_url,
            website_exists=True,
            overall_score=85,
            verdict=WebsiteVerdict.ADEQUATE,
            improvement_needed=False,
            improvement_reason="Website has modern visual style and fast load times.",
            status='completed'
        )
        db.session.add(analysis)
        db.session.commit()

        res = generate_lead_prd(lead.id)
        assert res['success'] is False
        assert res['code'] == 'adequate_website'

        # Confirm no PRD entry exists
        assert PRD.query.filter_by(lead_id=lead.id).first() is None


def test_revise_prd_ai_chat(app):
    """Test revising a PRD via admin chat instructions."""
    with app.app_context():
        lead = Lead(business_name="Desert Bakery", business_category="bakery", website_url="")
        db.session.add(lead)
        db.session.commit()

        # Seed initial PRD
        prd = PRD(
            lead_id=lead.id,
            title="Sitemap draft",
            business_overview="Original overview",
            current_version=1,
            status=PRDStatus.UNDER_REVIEW
        )
        db.session.add(prd)
        db.session.commit()
        
        # Seed Version 1 snapshot
        v1 = PRDVersion(prd_id=prd.id, version=1, content_snapshot={"title": "Sitemap draft", "business_overview": "Original overview"})
        db.session.add(v1)
        db.session.commit()

        mock_revision_response = {
            "title": "Sitemap draft",
            "business_overview": "Original overview updated with premium wedding cake catering focus.",
            "business_analysis": "",
            "website_goal": "",
            "target_audience": "",
            "design_direction": "",
            "site_structure": "",
            "functional_requirements": "",
            "content_requirements": "",
            "cta_strategy": "",
            "technical_requirements": ""
        }

        with patch('app.services.prd_service.llm_router.generate_structured_output', return_value=mock_revision_response):
            res = revise_prd_with_ai(prd.id, "Focus on premium wedding cake catering", user_id=None)
            assert res['success'] is True
            assert res['version'] == 2

            # Check DB changes
            db.session.refresh(prd)
            assert prd.current_version == 2
            assert "wedding cake catering" in prd.business_overview
            
            v2 = PRDVersion.query.filter_by(prd_id=prd.id, version=2).first()
            assert v2 is not None
            assert v2.author_type == 'ai'
            assert "wedding cake catering" in v2.content_snapshot['business_overview']
