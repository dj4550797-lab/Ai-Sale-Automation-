"""
Flixora AI Sales Automation Agent — Lead Service

Handles lead discovery process, duplicate filtering, scoring, and persistence.
"""
import os
from datetime import datetime, timezone
from app.extensions import db
from app.models import Lead, LeadContact, LeadSource, APICredential
from app.constants import LeadStatus
from app.integrations.maps.google_places import GooglePlacesProvider
from app.utils.duplicate_detector import check_for_duplicate
from app.utils.logger import get_logger

logger = get_logger('services')


def run_lead_discovery(location, category, daily_target=20, min_rating=None, require_website=False):
    """
    Search and discover leads using Google Places integration with page token looping.
    Saves unique leads, updates likely duplicates, and respects daily targets.
    """
    from zoneinfo import ZoneInfo
    from app.models import Setting

    # 1. Fetch Google Maps API Key
    cred = APICredential.query.filter_by(service_name='google_maps').first()
    api_key = ''
    if cred:
        from app.security.encryption import decrypt_value
        api_key = decrypt_value(cred.encrypted_value)
    else:
        api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '')

    if not api_key:
        logger.error("Google Maps API Key is not configured.")
        return {"success": False, "error": "Google Maps API Key not configured. Please add it to Settings -> Integrations."}

    # 2. Get daily limit setting dynamically
    limit_setting = Setting.query.filter_by(category='lead_discovery', key='daily_lead_target').first()
    daily_limit = int(limit_setting.value) if limit_setting else daily_target
    
    # 3. Calculate timezone-aware discovered today count
    tz_setting = Setting.query.filter_by(category='agent', key='timezone').first()
    tz_name = tz_setting.value if tz_setting else 'UTC'
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo('UTC')
        
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    
    leads_today = Lead.query.filter(Lead.created_at >= start_utc).count()
    remaining_capacity = max(0, daily_limit - leads_today)
    
    if remaining_capacity <= 0:
        logger.info(f"Daily lead target reached today ({leads_today}/{daily_limit}). Skipping discovery.")
        return {
            "success": True,
            "processed_count": 0,
            "saved_count": 0,
            "duplicate_count": 0,
            "leads": [],
            "message": f"Daily target reached today ({leads_today}/{daily_limit})."
        }

    # 4. Search Loop using nextPageToken
    provider = GooglePlacesProvider(api_key=api_key)
    logger.info(f"Launching Places Search: {category} in {location} (Target remaining: {remaining_capacity})")
    
    saved_count = 0
    duplicate_count = 0
    processed_leads = []
    page_token = None
    
    while saved_count < remaining_capacity:
        # Fetch page of results
        raw_results, next_page_token = provider.search_businesses(
            location=location,
            category=category,
            limit=min(20, remaining_capacity - saved_count + 5),  # Request slightly more to cover duplicates
            page_token=page_token
        )
        
        if not raw_results:
            break
            
        for item in raw_results:
            if saved_count >= remaining_capacity:
                break
                
            # Filter by min rating if specified
            if min_rating and item.get('rating') and item['rating'] < float(min_rating):
                continue
            
            # Filter by require website if specified
            if require_website and not item.get('website_url'):
                continue
                
            # Check duplicates
            verdict = check_for_duplicate(item)
            if verdict['status'] == 'confirmed_duplicate':
                duplicate_count += 1
                logger.info(f"Skipping duplicate Place ID: {item.get('google_place_id')}")
                continue
                
            lead_score = _calculate_lead_score(item)
            
            if verdict['status'] == 'likely_duplicate':
                existing_lead = Lead.query.get(verdict['matched_lead_id'])
                if existing_lead:
                    existing_lead.rating = item.get('rating')
                    existing_lead.review_count = item.get('review_count')
                    existing_lead.lead_score = lead_score
                    existing_lead.last_action = "Updated via discovery rerun"
                    db.session.commit()
                    processed_leads.append(existing_lead)
                    duplicate_count += 1
                continue
                
            # Save new unique lead
            lead = Lead(
                business_name=item['business_name'],
                business_category=item['business_category'],
                description=item.get('description', ''),
                address=item['address'],
                website_url=item['website_url'],
                rating=item['rating'],
                review_count=item['review_count'],
                google_place_id=item['google_place_id'],
                business_hours=item.get('business_hours', ''),
                lead_score=lead_score,
                status=LeadStatus.NEW,
                last_action="Discovered via lead search"
            )
            db.session.add(lead)
            db.session.commit()
            
            # Save phone
            if item.get('phone'):
                contact = LeadContact(
                    lead_id=lead.id,
                    contact_type='phone',
                    value=item['phone'],
                    is_primary=True
                )
                db.session.add(contact)
                
            # Save source
            source = LeadSource(
                lead_id=lead.id,
                source_type='google_places',
                source_query=f"{category} in {location}",
                source_location=location,
                source_category=category
            )
            db.session.add(source)
            db.session.commit()
            
            # Auto enrichment and analysis
            from app.services.pipeline_service import process_lead_pipeline
            try:
                process_lead_pipeline(lead.id)
            except Exception as pipeline_err:
                logger.error(f"Failed to execute pipeline for lead {lead.id}: {pipeline_err}")
                
            processed_leads.append(lead)
            saved_count += 1
            
        if not next_page_token:
            break
        page_token = next_page_token
        
    return {
        "success": True,
        "processed_count": saved_count + duplicate_count,
        "saved_count": saved_count,
        "duplicate_count": duplicate_count,
        "leads": [l.id for l in processed_leads]
    }


def _calculate_lead_score(item):
    """
    Calculate lead qualification priority score (§23).
    Higher scores imply higher sales priority (poor website, low rating).
    """
    score = 50  # Baseline
    
    # Missing website is prime target (+30 points)
    if not item.get('website_url'):
        score += 30
        
    # Low rating implies need for review management or marketing refresh
    rating = item.get('rating')
    if rating:
        if rating < 4.0:
            score += 20
        elif rating < 4.5:
            score += 10
            
    # Small review volume is a selling point (+15 points)
    reviews = item.get('review_count', 0)
    if reviews < 15:
        score += 15
        
    return min(score, 100)
