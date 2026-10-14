"""
Flixora AI Sales Automation Agent — Lead Views and Filters Tests
"""
import pytest
from app import create_app
from app.extensions import db
from app.models import Lead, LeadContact, LeadSource
from app.constants import LeadStatus
from app.services.auth_service import create_admin_user
from app.services.lead_service import _calculate_lead_score


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


def test_lead_score_calculation():
    """Test score prioritizations based on website presence and ratings (§23)."""
    # 1. Missing website, poor rating (Rating 3.5, no website) -> baseline(50) + no_web(30) + low_rating(20) = 100
    item1 = {'website_url': '', 'rating': 3.5, 'review_count': 10}
    assert _calculate_lead_score(item1) == 100
    
    # 2. Has website, good rating -> baseline(50) + reviews(<15)(15) = 65
    item2 = {'website_url': 'http://oksite.com', 'rating': 4.7, 'review_count': 5}
    assert _calculate_lead_score(item2) == 65


def test_leads_list_searching_and_filtering(client, app):
    """Test searching and filtering in lead list view."""
    # Login
    client.post('/login', data={'username': 'testadmin', 'password': 'password123'})
    
    # Insert test data
    with app.app_context():
        lead1 = Lead(business_name="Green Valley Restaurant", business_category="restaurant", rating=4.2, address="Dwarka", status=LeadStatus.NEW, lead_score=70)
        lead2 = Lead(business_name="Super Dental Clinic", business_category="dentist", rating=3.8, address="Indiranagar", status=LeadStatus.QUALIFIED, lead_score=90)
        db.session.add_all([lead1, lead2])
        db.session.commit()

    # Test unfiltered list
    response = client.get('/leads')
    assert response.status_code == 200
    assert b"Green Valley Restaurant" in response.data
    assert b"Super Dental Clinic" in response.data

    # Test search query
    response_search = client.get('/leads?search=Dental')
    assert b"Super Dental Clinic" in response.data
    assert b"Green Valley Restaurant" not in response_search.data

    # Test category filter
    response_cat = client.get('/leads?category=restaurant')
    assert b"Green Valley Restaurant" in response_cat.data
    assert b"Super Dental Clinic" not in response_cat.data

    # Test status filter
    response_status = client.get('/leads?status=qualified')
    assert b"Super Dental Clinic" in response_status.data
    assert b"Green Valley Restaurant" not in response_status.data
