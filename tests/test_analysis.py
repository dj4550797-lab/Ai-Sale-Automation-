"""
Flixora AI Sales Automation Agent — Website Analysis Tests
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import Lead, WebsiteAnalysis
from app.constants import LeadStatus, WebsiteVerdict
from app.services.auth_service import create_admin_user
from app.services.analysis_service import analyze_lead_website


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        create_admin_user(username='testadmin', email='test@flixora.com', password='password')
        yield app
        db.session.remove()
        db.drop_all()


def test_analysis_skipped_when_no_website(app):
    """Test that website analysis is marked as completed/no_website immediately if URL is missing."""
    with app.app_context():
        # Setup lead with empty website_url
        lead = Lead(business_name="Webless Diner", business_category="restaurant", website_url="")
        db.session.add(lead)
        db.session.commit()

        res = analyze_lead_website(lead.id)
        assert res['success'] is True
        assert "Skipped existing site analysis" in res['message']

        # Verify entry in db
        analysis = WebsiteAnalysis.query.filter_by(lead_id=lead.id).first()
        assert analysis is not None
        assert analysis.website_exists is False
        assert analysis.verdict == WebsiteVerdict.NO_WEBSITE
        assert analysis.improvement_needed is True
        assert "No website exists" in analysis.improvement_reason
        assert lead.website_exists is False


def test_analysis_success_flow(app):
    """Test successful scraping and LLM analysis flow."""
    with app.app_context():
        lead = Lead(
            business_name="Connaught Salon", 
            business_category="salon", 
            website_url="http://connaughtsalon.com"
        )
        db.session.add(lead)
        db.session.commit()

        # Mock LLM structured output response
        mock_llm_response = {
            "visual_design_score": 45,
            "layout_score": 50,
            "typography_score": 60,
            "branding_score": 55,
            "mobile_score": 40,
            "navigation_score": 70,
            "cta_score": 30,
            "contact_flow_score": 65,
            "service_presentation_score": 50,
            "trust_signals_score": 40,
            "performance_score": 50,
            "accessibility_score": 60,
            "conversion_score": 35,
            "overall_score": 48,
            "verdict": "needs_improvement",
            "improvement_needed": True,
            "improvement_reason": "Poor mobile responsiveness and missing CTA buttons.",
            "observed_facts": ["No Booking button found", "Mobile menu collapses incorrectly"],
            "ai_recommendations": ["Add a visible CTA Booking header", "Use responsive grid styling"],
            "ai_inferences": ["Loses around 40% of mobile search engine traffic"]
        }

        with patch('app.services.analysis_service.llm_router.generate_structured_output', return_value=mock_llm_response) as mock_llm:
            res = analyze_lead_website(lead.id)
            assert res['success'] is True
            assert res['verdict'] == WebsiteVerdict.NEEDS_IMPROVEMENT

            # Check DB values
            analysis = WebsiteAnalysis.query.filter_by(lead_id=lead.id).first()
            assert analysis is not None
            assert analysis.overall_score == 48
            assert analysis.visual_design_score == 45
            assert analysis.improvement_needed is True
            assert len(analysis.observed_facts) == 2
            assert lead.website_exists is True
            assert lead.last_action == "Website analysis completed"
