"""
Flixora AI Sales Automation Agent — Enrichment & Pipeline Tests
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import Lead, LeadContact, SocialProfile, WebsiteAnalysis, PRD, UploadedFile, APICredential
from app.constants import LeadStatus, PRDStatus, WebsiteVerdict
from app.services.auth_service import create_admin_user
from app.services.pipeline_service import process_lead_pipeline, generate_lead_dossier_text
from app.services.lead_service import run_lead_discovery


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


# ── CONTACT ENRICHMENT TESTS ───────────────────────────────────────────

def test_google_places_contact_normalization(app):
    """Test 1: Google Places contact normalization includes description and hours."""
    from app.integrations.maps.google_places import GooglePlacesProvider
    provider = GooglePlacesProvider(api_key="test-key")
    
    mock_place_raw = {
        "id": "place-123",
        "displayName": {"text": "Beauty Salon"},
        "primaryType": "salon",
        "formattedAddress": "123 Main St",
        "nationalPhoneNumber": "123-456-7890",
        "websiteUri": "http://beautysalon.com",
        "rating": 4.5,
        "userRatingCount": 20,
        "editorialSummary": {"text": "A beautiful local salon"},
        "regularOpeningHours": {"weekdayDescriptions": ["Mon-Fri: 9-5"]}
    }
    
    res = provider._normalize_place_data(mock_place_raw)
    assert res['business_name'] == "Beauty Salon"
    assert res['description'] == "A beautiful local salon"
    assert res['business_hours'] == "Mon-Fri: 9-5"
    assert res['phone'] == "123-456-7890"


def test_phone_and_email_extraction(app):
    """Test 2 & 3: Extraction of phone and email from parsed website text."""
    with app.app_context():
        lead = Lead(business_name="Sal", website_url="http://sal.com")
        db.session.add(lead)
        db.session.commit()

        mock_scrape = {
            "success": True,
            "detected_phones": ["9876543210"],
            "detected_emails": ["info@sal.com"],
            "detected_socials": [],
            "detected_bookings": [],
            "detected_owners": []
        }
        
        with patch('app.services.pipeline_service.scrape_website', return_value=mock_scrape):
            from app.services.pipeline_service import enrich_lead_contacts
            enrich_lead_contacts(lead)
            
            phone = LeadContact.query.filter_by(lead_id=lead.id, contact_type='phone').first()
            email = LeadContact.query.filter_by(lead_id=lead.id, contact_type='email').first()
            assert phone.value == "9876543210"
            assert email.value == "info@sal.com"


def test_website_contact_extraction_social_and_booking(app):
    """Test 4 & 5: Website contact extraction of social links and booking URLs."""
    with app.app_context():
        lead = Lead(business_name="Sal", website_url="http://sal.com")
        db.session.add(lead)
        db.session.commit()

        mock_scrape = {
            "success": True,
            "detected_phones": [],
            "detected_emails": [],
            "detected_socials": ["https://instagram.com/sal", "https://facebook.com/sal"],
            "detected_bookings": ["https://sal.com/book"],
            "detected_owners": []
        }
        
        with patch('app.services.pipeline_service.scrape_website', return_value=mock_scrape):
            from app.services.pipeline_service import enrich_lead_contacts
            enrich_lead_contacts(lead)
            
            ig = SocialProfile.query.filter_by(lead_id=lead.id, platform='instagram').first()
            fb = SocialProfile.query.filter_by(lead_id=lead.id, platform='facebook').first()
            book = LeadContact.query.filter_by(lead_id=lead.id, contact_type='booking_url').first()
            
            assert ig.profile_url == "https://instagram.com/sal"
            assert fb.profile_url == "https://facebook.com/sal"
            assert book.value == "https://sal.com/book"


def test_unknown_fields_remain_unavailable(app):
    """Test 6 & 7: Unknown fields remain unavailable, no fabricated owner/contact info."""
    with app.app_context():
        lead = Lead(business_name="Hidden Corp", website_url="http://hidden.com")
        db.session.add(lead)
        db.session.commit()

        mock_scrape = {
            "success": True,
            "detected_phones": [],
            "detected_emails": [],
            "detected_socials": [],
            "detected_bookings": [],
            "detected_owners": []
        }
        
        with patch('app.services.pipeline_service.scrape_website', return_value=mock_scrape):
            from app.services.pipeline_service import enrich_lead_contacts
            enrich_lead_contacts(lead)
            
            contacts = LeadContact.query.filter_by(lead_id=lead.id).all()
            socials = SocialProfile.query.filter_by(lead_id=lead.id).all()
            assert len(contacts) == 0
            assert len(socials) == 0


# ── AUTOMATIC PIPELINE TESTS ───────────────────────────────────────────

def test_discovery_automatically_triggers_enrichment_and_analysis(app):
    """Test 8, 9, 10: Discovery triggers contacts enrichment, website analysis, and PRD generation."""
    with app.app_context():
        mock_places = [
            {
                "business_name": "Dynamic Cafe",
                "business_category": "restaurant",
                "address": "456 Main St",
                "phone": "444-555-6666",
                "website_url": "http://dynamiccafe.com",
                "rating": 3.8,
                "review_count": 5,
                "google_place_id": "google-cafe-1",
                "description": "Lovely coffee",
                "business_hours": "Mon-Sat"
            }
        ]

        mock_scrape = {
            "success": True,
            "detected_phones": ["444-555-6666"],
            "detected_emails": ["owner@dynamiccafe.com"],
            "detected_socials": ["https://instagram.com/dynamiccafe"],
            "detected_bookings": [],
            "detected_owners": ["Alice Brown"]
        }

        mock_analysis = {
            "visual_design_score": 60,
            "layout_score": 65,
            "typography_score": 70,
            "branding_score": 50,
            "mobile_score": 55,
            "navigation_score": 60,
            "cta_score": 40,
            "contact_flow_score": 50,
            "service_presentation_score": 60,
            "trust_signals_score": 30,
            "performance_score": 50,
            "accessibility_score": 60,
            "conversion_score": 40,
            "overall_score": 54,
            "verdict": "needs_improvement",
            "improvement_needed": True,
            "improvement_reason": "Poor design",
            "observed_facts": ["No booking buttons"],
            "ai_recommendations": ["Rebuild site"],
            "ai_inferences": ["Losing clients"]
        }

        mock_prd = {
            "title": "Dynamic Cafe PRD Draft",
            "business_overview": "Overview of Cafe",
            "business_analysis": "Needs overhaul",
            "website_goal": "More reservations",
            "target_audience": "Local foodies",
            "design_direction": "Warm layout",
            "site_structure": "Sitemap details",
            "functional_requirements": "Reservation form",
            "content_requirements": "Menu photos",
            "cta_strategy": "Book buttons",
            "technical_requirements": "Hosting setup"
        }

        # Seed Google Maps credential in database
        from app.security.encryption import encrypt_value
        cred = APICredential(
            service_name='google_maps',
            credential_type='api_key',
            encrypted_value=encrypt_value("valid-google-key")
        )
        db.session.add(cred)
        db.session.commit()

        def llm_side_effect(prompt, schema, task_type=None):
            if task_type == 'website_analysis':
                return mock_analysis
            elif task_type == 'prd_generation':
                return mock_prd
            return {}

        with patch('app.services.lead_service.GooglePlacesProvider.search_businesses', return_value=(mock_places, None)), \
             patch('app.services.pipeline_service.scrape_website', return_value=mock_scrape), \
             patch('app.ai.llm_router.llm_router.generate_structured_output', side_effect=llm_side_effect):
            
            res = run_lead_discovery("Gurgaon", "restaurant", daily_target=1)
            assert res['success'] is True
            assert res['saved_count'] == 1
            
            lead = Lead.query.filter_by(google_place_id="google-cafe-1").first()
            assert lead is not None
            
            # Verify enrichment saved
            email = LeadContact.query.filter_by(lead_id=lead.id, contact_type='email').first()
            assert email.value == "owner@dynamiccafe.com"
            
            # Verify analysis ran
            analysis = WebsiteAnalysis.query.filter_by(lead_id=lead.id).first()
            assert analysis is not None
            assert analysis.overall_score == 54
            
            # Verify PRD generated
            prd = PRD.query.filter_by(lead_id=lead.id).first()
            assert prd is not None
            assert prd.title == "Dynamic Cafe PRD Draft"
            
            # Verify TXT dossier exists
            dossier = UploadedFile.query.filter_by(lead_id=lead.id).filter(UploadedFile.original_filename.like('LEAD-%.txt')).first()
            assert dossier is not None
            assert os.path.exists(os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], 'documents', dossier.filename)))

            # Cleanup dossier file
            os.remove(os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], 'documents', dossier.filename)))


def test_prd_is_lead_specific(app):
    """Test 11: Ensure PRD is isolated and lead-specific."""
    with app.app_context():
        lead1 = Lead(business_name="Shop A", website_url="http://shopa.com")
        lead2 = Lead(business_name="Shop B", website_url="http://shopb.com")
        db.session.add_all([lead1, lead2])
        db.session.commit()

        # Seed different PRDs
        prd1 = PRD(lead_id=lead1.id, title="PRD for Shop A", status=PRDStatus.APPROVED)
        prd2 = PRD(lead_id=lead2.id, title="PRD for Shop B", status=PRDStatus.UNDER_REVIEW)
        db.session.add_all([prd1, prd2])
        db.session.commit()

        assert PRD.query.filter_by(lead_id=lead1.id).first().title == "PRD for Shop A"
        assert PRD.query.filter_by(lead_id=lead2.id).first().title == "PRD for Shop B"


def test_txt_dossier_contains_actual_stored_information(app):
    """Test 12 & 13: Dossier generation contains actual data, not fabricated info."""
    with app.app_context():
        lead = Lead(
            business_name="Real Niche Shop",
            business_category="clothing",
            website_url="http://nicheshop.com",
            lead_score=75,
            google_place_id="real-place-999"
        )
        db.session.add(lead)
        db.session.commit()

        contact = LeadContact(lead_id=lead.id, contact_type='phone', value='555-555-5555')
        db.session.add(contact)
        db.session.commit()

        dossier_text = generate_lead_dossier_text(lead)
        
        assert "Business Name: Real Niche Shop" in dossier_text
        assert "Category: clothing" in dossier_text
        assert "Phone: 555-555-5555" in dossier_text
        assert "Google Place ID: real-place-999" in dossier_text
        assert "Email: Not found" in dossier_text


def test_txt_download_works(app, client):
    """Test 14: Dossier download route returns text file attachment."""
    with app.app_context():
        lead = Lead(business_name="Download Shop", website_url="http://download.com")
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

        # Generate dossier
        dossier_text = "COMPLETE DOSSIER TEST"
        from app.services.file_service import save_generated_file
        save_res = save_generated_file(
            file_content=dossier_text,
            original_filename="LEAD-9999_download.txt",
            file_type='document',
            lead_id=lead_id
        )
        assert save_res['success'] is True

    # Login and download
    client.post('/login', data={'username': 'testadmin', 'password': 'password'})
    res = client.get(f'/leads/{lead_id}/download-dossier')
    assert res.status_code == 200
    assert b"COMPLETE DOSSIER TEST" in res.data
    assert "attachment" in res.headers["Content-Disposition"]
    res.close()

    # Cleanup
    with app.app_context():
        dossier = UploadedFile.query.filter_by(lead_id=lead_id).first()
        os.remove(os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], 'documents', dossier.filename)))


# ── FAILURE HANDLING TESTS ─────────────────────────────────────────────

def test_pipeline_failure_isolation_website_unavailable(app):
    """Test 15: Website unavailable does not prevent lead creation and dossier compile."""
    with app.app_context():
        lead = Lead(business_name="Closed Shop", website_url="http://closedurl-doesnotexist.com")
        db.session.add(lead)
        db.session.commit()

        # Run pipeline where scraper fails
        mock_scrape = {"success": False, "error": "DNS resolution failed"}
        with patch('app.services.pipeline_service.scrape_website', return_value=mock_scrape):
            res = process_lead_pipeline(lead.id)
            assert res['success'] is True
            
            # Lead remains in DB
            db_lead = Lead.query.get(lead.id)
            assert db_lead is not None
            
            # Website analysis status = failed
            analysis = WebsiteAnalysis.query.filter_by(lead_id=lead.id).first()
            assert analysis.status == 'failed'
            
            # Dossier still generated
            dossier = UploadedFile.query.filter_by(lead_id=lead.id).first()
            assert dossier is not None
            os.remove(os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], 'documents', dossier.filename)))


def test_pipeline_failure_isolation_prd_fails(app):
    """Test 18 & 19: PRD failure does not destroy the lead or prevent dossier generation."""
    with app.app_context():
        lead = Lead(business_name="Prd Fail Shop", website_url="")
        db.session.add(lead)
        db.session.commit()

        # Force generate_lead_prd to raise exception
        with patch('app.services.pipeline_service.generate_lead_prd', side_effect=ValueError("LLM Overloaded")):
            res = process_lead_pipeline(lead.id)
            assert res['success'] is True
            
            db_lead = Lead.query.get(lead.id)
            assert db_lead is not None
            
            # Dossier still generated
            dossier = UploadedFile.query.filter_by(lead_id=lead.id).first()
            assert dossier is not None
            os.remove(os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], 'documents', dossier.filename)))
