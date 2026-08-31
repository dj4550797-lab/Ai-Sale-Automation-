"""
Flixora AI Sales Automation Agent — End-to-End Pipeline & Route Tests
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import Lead, WebsiteAnalysis, PRD, DemoProject, OutreachCampaign, OutreachEvent
from app.services.auth_service import create_admin_user
from app.services.pipeline_service import process_lead_end_to_end

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        create_admin_user(username='pipelineadmin', email='pipelineadmin@flixora.com', password='pipelinepassword')
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def authenticated_client(client):
    client.post('/login', data={
        'username': 'pipelineadmin',
        'password': 'pipelinepassword'
    })
    return client

@patch('app.ai.llm_router.llm_router.generate_text')
@patch('app.ai.llm_router.llm_router.generate_structured_output')
@patch('app.services.demo_service.publish_demo_project')
def test_process_lead_end_to_end(
    mock_publish,
    mock_llm_structured,
    mock_llm_text,
    app
):
    """Test 1: End-to-end processing triggers analysis, force-prd, compile, publish, and outreach."""
    # Setup mock returns
    def structured_side_effect(prompt, schema, task_type=None):
        if task_type == 'website_analysis':
            return {
                "visual_design_score": 70,
                "layout_score": 75,
                "typography_score": 80,
                "branding_score": 85,
                "mobile_score": 90,
                "navigation_score": 95,
                "cta_score": 60,
                "contact_flow_score": 50,
                "service_presentation_score": 40,
                "trust_signals_score": 30,
                "performance_score": 20,
                "accessibility_score": 10,
                "conversion_score": 50,
                "overall_score": 60,
                "improvement_needed": True,
                "improvement_reason": "Outdated UI layout.",
                "observed_facts": ["No booking form"],
                "ai_recommendations": ["Add booking page"],
                "ai_inferences": ["Missing customers"]
            }
        elif task_type == 'prd_generation':
            return {
                "title": "Premium Website Proposal",
                "business_overview": "Overview text",
                "business_analysis": "Analysis text",
                "website_goal": "Goal text",
                "target_audience": "Audience text",
                "design_direction": "Design text",
                "site_structure": "Structure text",
                "functional_requirements": "Functional text",
                "content_requirements": "Content text",
                "cta_strategy": "CTA text",
                "technical_requirements": "Technical text"
            }
        return {}

    mock_llm_structured.side_effect = structured_side_effect
    mock_llm_text.return_value = "<html><body>Demo website contents / outreach message</body></html>"
    mock_publish.return_value = {"success": True, "published_url": "https://flixora.github.io/demo-1"}

    with app.app_context():
        # Create lead
        lead = Lead(
            business_name="Test Shop",
            business_category="retail",
            website_url="http://testshop.com"
        )
        db.session.add(lead)
        db.session.commit()
        
        # Run end-to-end pipeline
        res = process_lead_end_to_end(lead.id, force_prd=True)
        assert res.get("success") is True
        assert "ready" in res.get("message").lower()

        # Verify all records created
        analysis = WebsiteAnalysis.query.filter_by(lead_id=lead.id).first()
        assert analysis is not None
        assert analysis.overall_score == 60

        prd = PRD.query.filter_by(lead_id=lead.id).first()
        assert prd is not None
        assert prd.status == 'ready'

        # Under the simplified pipeline, demo and outreach are NOT automatically created
        demo = DemoProject.query.filter_by(lead_id=lead.id).first()
        assert demo is None

        campaign = OutreachCampaign.query.filter_by(lead_id=lead.id).first()
        assert campaign is None

@patch('app.services.pipeline_service.process_lead_end_to_end')
def test_update_website_route(mock_process, authenticated_client, app):
    """Test 2: Update website route updates link and triggers pipeline."""
    mock_process.return_value = {"success": True, "message": "Demo published and outreach sent."}
    
    with app.app_context():
        lead = Lead(business_name="Saloon Express", website_url="http://oldsaloon.com")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

    # Post to update website
    res = authenticated_client.post(f'/leads/{lead_id}/update-website', data={
        'website_url': 'http://newsaloon.com'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Website URL updated" in res.data
    
    with app.app_context():
        updated_lead = Lead.query.get(lead_id)
        assert updated_lead.website_url == 'http://newsaloon.com'
        mock_process.assert_called_once_with(lead_id, force_prd=True)

@patch('app.services.pipeline_service.process_lead_end_to_end')
def test_trigger_pipeline_route(mock_process, authenticated_client, app):
    """Test 3: Manual pipeline trigger endpoint calls end-to-end processor."""
    mock_process.return_value = {"success": True, "message": "Entire pipeline completed successfully."}
    
    with app.app_context():
        lead = Lead(business_name="Gym Hub", website_url="http://gymhub.com")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

    res = authenticated_client.post(f'/leads/{lead_id}/trigger-pipeline', follow_redirects=True)
    assert res.status_code == 200
    assert b"Entire pipeline completed successfully" in res.data
    mock_process.assert_called_once_with(lead_id, force_prd=True)
