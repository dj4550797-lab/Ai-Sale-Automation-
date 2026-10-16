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
    
    # If caller specifies an explicit target count, use it directly (e.g. manual discovery or forced run)
    if daily_target and daily_target > 0:
        remaining_capacity = daily_target
    else:
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
    processed_lead_ids = []
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
                
            # Check duplicates with session safety
            try:
                verdict = check_for_duplicate(item)
            except Exception as dup_err:
                db.session.rollback()
                logger.warning(f"Error checking duplicate for {item.get('business_name')}: {dup_err}")
                verdict = {'status': 'new'}

            if verdict.get('status') == 'confirmed_duplicate':
                duplicate_count += 1
                logger.info(f"Skipping duplicate Place ID: {item.get('google_place_id')}")
                continue
                
            lead_score = _calculate_lead_score(item)
            
            if verdict.get('status') == 'likely_duplicate':
                try:
                    matched_id = verdict.get('matched_lead_id')
                    existing_lead = db.session.get(Lead, matched_id) if matched_id else None
                    if existing_lead:
                        existing_lead.rating = item.get('rating')
                        existing_lead.review_count = item.get('review_count')
                        existing_lead.lead_score = lead_score
                        existing_lead.last_action = "Updated via discovery rerun"
                        db.session.commit()
                        processed_lead_ids.append(matched_id)
                        duplicate_count += 1
                except Exception as update_err:
                    db.session.rollback()
                    logger.error(f"Error updating duplicate lead: {update_err}")
                continue
                
            # Save new unique lead with per-lead transaction isolation
            try:
                # Double check unique google_place_id to prevent Postgres constraint violations
                place_id = item.get('google_place_id')
                if place_id:
                    existing_by_place = Lead.query.filter_by(google_place_id=place_id).first()
                    if existing_by_place:
                        duplicate_count += 1
                        logger.info(f"Skipping already-existing Place ID: {place_id}")
                        continue

                lead = Lead(
                    business_name=item['business_name'],
                    business_category=item['business_category'],
                    description=item.get('description', ''),
                    address=item['address'],
                    city=item.get('city', ''),
                    state=item.get('state', ''),
                    country=item.get('country', ''),
                    postal_code=item.get('postal_code', ''),
                    website_url=item.get('website_url'),
                    rating=item.get('rating'),
                    review_count=item.get('review_count'),
                    google_place_id=item.get('google_place_id'),
                    business_hours=item.get('business_hours', ''),
                    lead_score=lead_score,
                    status=LeadStatus.NEW,
                    last_action="Discovered via lead search"
                )
                db.session.add(lead)
                db.session.commit()
                new_lead_id = lead.id
                
                # Save phone
                if item.get('phone'):
                    contact = LeadContact(
                        lead_id=new_lead_id,
                        contact_type='phone',
                        value=item['phone'],
                        is_primary=True
                    )
                    db.session.add(contact)
                    
                # Save source
                source = LeadSource(
                    lead_id=new_lead_id,
                    source_type='google_places',
                    source_query=f"{category} in {location}",
                    source_location=location,
                    source_category=category
                )
                db.session.add(source)
                db.session.commit()
                
                # Auto enrichment and analysis with failure isolation
                from app.services.pipeline_service import process_lead_pipeline
                try:
                    process_lead_pipeline(new_lead_id)
                except Exception as pipeline_err:
                    db.session.rollback()
                    logger.error(f"Failed to execute pipeline for lead {new_lead_id}: {pipeline_err}")
                    
                processed_lead_ids.append(new_lead_id)
                saved_count += 1
            except Exception as save_err:
                db.session.rollback()
                logger.error(f"Failed to save discovered lead {item.get('business_name')}: {save_err}")
                continue
            
        if not next_page_token:
            break
        page_token = next_page_token
        
    return {
        "success": True,
        "processed_count": saved_count + duplicate_count,
        "saved_count": saved_count,
        "duplicate_count": duplicate_count,
        "leads": processed_lead_ids
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


def purge_lead_safely(lead_id):
    """
    Safely delete a lead and cascade all relationships in foreign-key dependency order.
    Ensures that cross-table foreign key constraints (such as outreach_campaigns.demo_id,
    sales_deals.demo_id, sales_deals.prd_id, followups.outreach_id) never trigger ForeignKeyViolation.
    """
    from app.models import (
        Lead, OutreachCampaign, OutreachEvent, SalesDeal, FollowUp,
        DemoProject, PRD, UploadedFile, Conversation, Message
    )

    lead = Lead.query.get(lead_id)
    if not lead:
        return False

    # 1. Nullify demo references in outreach campaigns and sales deals
    demos = DemoProject.query.filter_by(lead_id=lead_id).all()
    demo_ids = [d.id for d in demos]
    if demo_ids:
        OutreachCampaign.query.filter(OutreachCampaign.demo_id.in_(demo_ids)).update({'demo_id': None}, synchronize_session=False)
        SalesDeal.query.filter(SalesDeal.demo_id.in_(demo_ids)).update({'demo_id': None}, synchronize_session=False)

    # 2. Nullify PRD references in sales deals and uploaded files
    prds = PRD.query.filter_by(lead_id=lead_id).all()
    prd_ids = [p.id for p in prds]
    if prd_ids:
        SalesDeal.query.filter(SalesDeal.prd_id.in_(prd_ids)).update({'prd_id': None}, synchronize_session=False)
        UploadedFile.query.filter(UploadedFile.prd_id.in_(prd_ids)).update({'prd_id': None}, synchronize_session=False)

    # 3. Clean up outreach campaigns & events & followups
    campaigns = OutreachCampaign.query.filter_by(lead_id=lead_id).all()
    camp_ids = [c.id for c in campaigns]
    if camp_ids:
        FollowUp.query.filter(FollowUp.outreach_id.in_(camp_ids)).update({'outreach_id': None}, synchronize_session=False)
        OutreachEvent.query.filter(OutreachEvent.campaign_id.in_(camp_ids)).delete(synchronize_session=False)
        OutreachCampaign.query.filter_by(lead_id=lead_id).delete(synchronize_session=False)

    # 4. Clean up disk demo assets if any
    try:
        import os, shutil
        from flask import current_app
        upload_base = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        demo_dir = os.path.join(upload_base, 'demos', str(lead_id))
        if os.path.exists(demo_dir):
            shutil.rmtree(demo_dir, ignore_errors=True)
    except Exception:
        pass

    # 5. Delete the lead
    db.session.delete(lead)
    return True

