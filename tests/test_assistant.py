"""
Flixora AI Sales Automation Agent — Admin AI Assistant Tests
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import Lead, PRD, User
from app.constants import PRDStatus, LeadStatus
from app.services.auth_service import create_admin_user
from app.services.assistant_service import (
    get_lead_analytics, get_sales_analytics, search_prds,
    answer_admin_query
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


@pytest.fixture
def client(app):
    return app.test_client()


def test_lead_analytics_tool(app):
    """Test get_lead_analytics tool yields correct database aggregates."""
    with app.app_context():
        lead1 = Lead(business_name="Connaught Salon", business_category="salon", status=LeadStatus.NEW)
        lead2 = Lead(business_name="PQR Dentist", business_category="dentist", status=LeadStatus.QUALIFIED)
        db.session.add_all([lead1, lead2])
        db.session.commit()

        stats = get_lead_analytics()
        assert stats['total_leads'] == 2
        assert stats['by_category']['salon'] == 1
        assert stats['by_category']['dentist'] == 1
        assert stats['by_status'][LeadStatus.NEW] == 1


def test_sales_analytics_tool(app):
    """Test get_sales_analytics tool retrieves funnel stage totals."""
    with app.app_context():
        lead = Lead(business_name="Won Business", business_category="restaurant", status=LeadStatus.WON)
        db.session.add(lead)
        db.session.commit()

        stats = get_sales_analytics()
        assert stats['deals_won'] == 1
        assert stats['negotiations'] == 0


def test_assistant_query_dispatch_flow(app):
    """Test the complete assistant question dispatch and answer generation loop."""
    with app.app_context():
        # Setup mock lead
        lead = Lead(business_name="Delhi Diner", business_category="restaurant", status=LeadStatus.NEW)
        db.session.add(lead)
        db.session.commit()

        # Mock intent classification to choose lead_analytics
        mock_intent = {
            "tool_to_call": "lead_analytics",
            "search_query": ""
        }
        
        # Mock final response text
        mock_reply = "We discovered 1 lead in the database today."

        with patch('app.services.assistant_service.llm_router.generate_structured_output', return_value=mock_intent) as mock_classify, \
             patch('app.services.assistant_service.llm_router.generate_text', return_value=mock_reply) as mock_text:
                 
            res = answer_admin_query("How many leads do we have today?")
            assert res['success'] is True
            assert res['tool_called'] == 'lead_analytics'
            assert res['reply'] == "We discovered 1 lead in the database today."
            
            # Assert classification and text gen were invoked
            mock_classify.assert_called_once()
            mock_text.assert_called_once()
