"""
Flixora AI Sales Automation Agent — Duplicate Detection Tests
"""
import pytest
from app import create_app
from app.extensions import db
from app.models import Lead, LeadContact
from app.utils.duplicate_detector import check_for_duplicate, clean_url_domain


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_clean_url_domain():
    """Test domain normalizer helper."""
    assert clean_url_domain("https://www.google.com/search") == "google.com"
    assert clean_url_domain("http://places.example.co.uk/") == "places.example.co.uk"
    assert clean_url_domain("www.salon.com") == "salon.com"
    assert clean_url_domain("") == ""


def test_dedup_by_place_id(app):
    """Test duplicate detection by Google Place ID."""
    with app.app_context():
        # Setup existing lead
        lead = Lead(
            business_name="Connaught Salon",
            google_place_id="ChIJf-fake-place-id-12345",
            address="Connaught Place, New Delhi",
            lead_score=60
        )
        db.session.add(lead)
        db.session.commit()

        # Input data with matching place ID
        incoming = {
            'business_name': 'Connaught Salon & Spa',
            'google_place_id': 'ChIJf-fake-place-id-12345',
            'address': 'Connaught Place, Delhi'
        }

        res = check_for_duplicate(incoming)
        assert res['status'] == 'confirmed_duplicate'
        assert res['matched_lead_id'] == lead.id
        assert "Place ID" in res['reason']


def test_dedup_by_phone(app):
    """Test duplicate detection by phone number."""
    with app.app_context():
        lead = Lead(business_name="Luxe Salon", address="Indiranagar, Bangalore", lead_score=50)
        db.session.add(lead)
        db.session.commit()

        contact = LeadContact(lead_id=lead.id, contact_type='phone', value="9876543210", notes="Manager")
        db.session.add(contact)
        db.session.commit()

        # Matching phone
        incoming = {
            'business_name': 'Luxe Hair Salon',
            'phone': '9876543210',
            'address': 'Indiranagar'
        }

        res = check_for_duplicate(incoming)
        assert res['status'] == 'confirmed_duplicate'
        assert res['matched_lead_id'] == lead.id
        assert "phone" in res['reason']


def test_dedup_by_website(app):
    """Test duplicate detection by website domain match."""
    with app.app_context():
        lead = Lead(
            business_name="Elite Dentist", 
            website_url="https://www.elitedentistry.in/about", 
            address="South Ext, Delhi",
            lead_score=50
        )
        db.session.add(lead)
        db.session.commit()

        # Matching domain
        incoming = {
            'business_name': 'Elite Dental Clinic',
            'website_url': 'http://elitedentistry.in/contact',
            'address': 'South Delhi'
        }

        res = check_for_duplicate(incoming)
        assert res['status'] == 'likely_duplicate'
        assert res['matched_lead_id'] == lead.id
        assert "domain" in res['reason']


def test_dedup_by_name_and_address(app):
    """Test duplicate detection by business name + address stub matching."""
    with app.app_context():
        lead = Lead(
            business_name="Ambience Cafe", 
            address="15, Sector 5, Dwarka, Delhi",
            lead_score=50
        )
        db.session.add(lead)
        db.session.commit()

        # Matching name and address stub
        incoming = {
            'business_name': 'Ambience Cafe',
            'address': '15, Sector 5, Dwarka, New Delhi'
        }

        res = check_for_duplicate(incoming)
        assert res['status'] == 'likely_duplicate'
        assert res['matched_lead_id'] == lead.id
        assert "address stub" in res['reason']


def test_unique_lead(app):
    """Test that a completely new business record is marked as unique."""
    with app.app_context():
        lead = Lead(business_name="Ambience Cafe", address="Dwarka, Delhi", lead_score=50)
        db.session.add(lead)
        db.session.commit()

        incoming = {
            'business_name': 'Other Cafe',
            'address': 'Indiranagar, Bangalore',
            'phone': '1112223334',
            'website_url': 'http://othercafe.com'
        }

        res = check_for_duplicate(incoming)
        assert res['status'] == 'unique'
        assert res['matched_lead_id'] is None
