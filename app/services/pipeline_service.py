"""
Flixora AI Sales Automation Agent — Automatic Lead Intelligence Pipeline Service
"""
import os
import json
import re
from datetime import datetime, timezone
from flask import current_app

from app.extensions import db
from app.models import Lead, LeadContact, SocialProfile, LeadSource, WebsiteAnalysis, PRD, UploadedFile, LeadQualification
from app.constants import LeadStatus, PRDStatus, WebsiteVerdict
from app.services.scraper_service import scrape_website
from app.services.analysis_service import analyze_lead_website
from app.services.prd_service import generate_lead_prd
from app.services.file_service import save_generated_file
from app.utils.logger import get_logger

logger = get_logger('services')


def process_lead_pipeline(lead_id):
    """
    Run complete automatic lead intelligence pipeline:
    Enrichment -> Scraping/Analysis -> Scoring -> PRD -> Dossier Compile -> Save
    Includes strict Failure Isolation.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        logger.error(f"Lead {lead_id} not found in pipeline processing.")
        return {"success": False, "error": "Lead not found."}

    logger.info(f"Starting automatic lead intelligence pipeline for: {lead.business_name} (ID: {lead.id})")

    # Step 1: Contact & Social Enrichment
    try:
        enrich_lead_contacts(lead)
    except Exception as e:
        logger.error(f"Error in lead contact enrichment for {lead.id}: {e}")

    # Step 2: Website Analysis
    try:
        if lead.website_url:
            analyze_lead_website(lead.id)
        else:
            # Create skipped/empty analysis record
            analyze_lead_website(lead.id)
    except Exception as e:
        logger.error(f"Error in website analysis for {lead.id}: {e}")

    # Step 3: Lead Re-scoring & Status Synchronization
    try:
        analysis = WebsiteAnalysis.query.filter_by(lead_id=lead.id).first()
        if analysis:
            # Dynamic re-scoring based on audit verdict
            if analysis.verdict == WebsiteVerdict.NO_WEBSITE:
                lead.lead_score = min(lead.lead_score + 10, 100)
            elif analysis.verdict == WebsiteVerdict.NEEDS_IMPROVEMENT:
                lead.lead_score = min(lead.lead_score + 5, 100)
            
            # Auto-transition status based on qualification
            if analysis.improvement_needed:
                lead.status = LeadStatus.WAITING_FOR_DEMO
            else:
                lead.status = LeadStatus.DISQUALIFIED
            db.session.commit()
    except Exception as e:
        logger.error(f"Error in lead scoring/status sync for {lead.id}: {e}")

    # Step 4: PRD Generation
    try:
        generate_lead_prd(lead.id)
    except Exception as e:
        logger.error(f"Error in PRD generation for {lead.id}: {e}")

    # Step 5: Complete TXT Dossier Generation & Storage
    try:
        dossier_content = generate_lead_dossier_text(lead)
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', lead.business_name.lower())
        filename = f"LEAD-{lead.id:06d}_{clean_name}.txt"
        
        # Check if dossier already exists and delete it to prevent duplicates
        existing_dossier = UploadedFile.query.filter_by(lead_id=lead.id, file_type='document').filter(UploadedFile.original_filename.like('LEAD-%_*.txt')).first()
        if existing_dossier:
            # Resolve absolute path and delete from disk
            abs_path = os.path.abspath(os.path.join(current_app.root_path, existing_dossier.file_path))
            if os.path.exists(abs_path):
                os.remove(abs_path)
            db.session.delete(existing_dossier)
            db.session.commit()

        save_res = save_generated_file(
            file_content=dossier_content,
            original_filename=filename,
            file_type='document',
            lead_id=lead.id
        )
        if save_res.get('success'):
            lead.last_action = "Lead complete dossier generated"
            lead.last_action_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.info(f"Dossier TXT saved for lead {lead.id} at {save_res.get('file_path')}")
        else:
            logger.error(f"Failed to save dossier TXT for lead {lead.id}: {save_res.get('error')}")
    except Exception as e:
        logger.error(f"Error generating TXT dossier for {lead.id}: {e}")

    logger.info(f"Pipeline finished for lead {lead.id}. Status: {lead.status}, Score: {lead.lead_score}")
    return {"success": True, "lead_id": lead.id}


def enrich_lead_contacts(lead):
    """
    Crawl business website if present and extract emails, phones, socials, booking URLs.
    Does NOT fabricate information. Uses existing scraper.
    """
    if not lead.website_url:
        logger.info(f"Skipping contact enrichment for {lead.id}: No website URL.")
        return

    scrape_res = scrape_website(lead.website_url)
    if not scrape_res.get('success'):
        logger.warn(f"Failed to scrape website for contact enrichment: {scrape_res.get('error')}")
        return

    # Extract & Save Emails
    detected_emails = scrape_res.get('detected_emails', [])
    for email in detected_emails:
        existing = LeadContact.query.filter_by(lead_id=lead.id, contact_type='email', value=email).first()
        if not existing:
            contact = LeadContact(
                lead_id=lead.id,
                contact_type='email',
                value=email,
                is_primary=True
            )
            db.session.add(contact)

    # Extract & Save Phone Numbers
    detected_phones = scrape_res.get('detected_phones', [])
    for phone in detected_phones:
        # Clean phone
        clean_phone = phone.strip()
        existing = LeadContact.query.filter_by(lead_id=lead.id, contact_type='phone', value=clean_phone).first()
        if not existing:
            contact = LeadContact(
                lead_id=lead.id,
                contact_type='phone',
                value=clean_phone
            )
            db.session.add(contact)

    # Extract & Save Owners/Contact Person
    detected_owners = scrape_res.get('detected_owners', [])
    for owner in detected_owners:
        existing = LeadContact.query.filter_by(lead_id=lead.id, contact_type='owner_name', value=owner).first()
        if not existing:
            contact = LeadContact(
                lead_id=lead.id,
                contact_type='owner_name',
                value=owner
            )
            db.session.add(contact)

    # Extract & Save Socials (Instagram & Facebook)
    detected_socials = scrape_res.get('detected_socials', [])
    for social in detected_socials:
        platform = 'other'
        if 'instagram.com' in social.lower():
            platform = 'instagram'
        elif 'facebook.com' in social.lower():
            platform = 'facebook'
            
        existing = SocialProfile.query.filter_by(lead_id=lead.id, platform=platform, profile_url=social).first()
        if not existing:
            profile = SocialProfile(
                lead_id=lead.id,
                platform=platform,
                profile_url=social,
                username=social.rsplit('/', 1)[-1] or platform
            )
            db.session.add(profile)

    # Extract & Save Booking URLs
    detected_bookings = scrape_res.get('detected_bookings', [])
    for booking in detected_bookings:
        existing = LeadContact.query.filter_by(lead_id=lead.id, contact_type='booking_url', value=booking).first()
        if not existing:
            contact = LeadContact(
                lead_id=lead.id,
                contact_type='booking_url',
                value=booking,
                notes='Online Appointment Scheduler Link'
            )
            db.session.add(contact)

    db.session.commit()
    logger.info(f"Enriched contacts for lead {lead.id} successfully.")


def generate_lead_dossier_text(lead):
    """
    Generate the complete lead TXT report matching the requested schema.
    Uses 'Not found' or 'Not configured' if data is unavailable.
    """
    # Fetch relations
    phone_contact = LeadContact.query.filter_by(lead_id=lead.id, contact_type='phone').first()
    email_contact = LeadContact.query.filter_by(lead_id=lead.id, contact_type='email').first()
    owner_contact = LeadContact.query.filter_by(lead_id=lead.id, contact_type='owner_name').first()
    
    instagram = SocialProfile.query.filter_by(lead_id=lead.id, platform='instagram').first()
    facebook = SocialProfile.query.filter_by(lead_id=lead.id, platform='facebook').first()
    youtube = SocialProfile.query.filter_by(lead_id=lead.id, platform='youtube').first()
    linkedin = SocialProfile.query.filter_by(lead_id=lead.id, platform='linkedin').first()
    other_socials = SocialProfile.query.filter(
        SocialProfile.lead_id == lead.id,
        ~SocialProfile.platform.in_(['instagram', 'facebook', 'youtube', 'linkedin'])
    ).all()
    
    source = LeadSource.query.filter_by(lead_id=lead.id).first()
    analysis = WebsiteAnalysis.query.filter_by(lead_id=lead.id).first()
    qualification = LeadQualification.query.filter_by(lead_id=lead.id).first()
    prd = PRD.query.filter_by(lead_id=lead.id).first()
    
    # Conversations & Outreach
    from app.models import Conversation, OutreachCampaign, DemoProject, Message
    conv = Conversation.query.filter_by(lead_id=lead.id).first()
    campaign = OutreachCampaign.query.filter_by(lead_id=lead.id).first()
    demo = DemoProject.query.filter_by(lead_id=lead.id).first()
    
    lines = []
    
    lines.append("--------------------------------")
    lines.append("BUSINESS INFORMATION")
    lines.append("--------------------------------")
    lines.append(f"Business Name: {lead.business_name or 'Not found'}")
    lines.append(f"Category: {lead.business_category or 'Not found'}")
    lines.append(f"Description: {lead.description or 'Not found'}")
    lines.append(f"Address: {lead.address or 'Not found'}")
    lines.append(f"City: {lead.city or 'Not found'}")
    lines.append(f"State: {lead.state or 'Not found'}")
    lines.append(f"Country: {lead.country or 'Not found'}")
    lines.append(f"Phone: {phone_contact.value if (phone_contact and phone_contact.value) else 'Not found'}")
    lines.append(f"Email: {email_contact.value if (email_contact and email_contact.value) else 'Not found'}")
    lines.append(f"Website: {lead.website_url or 'Not found'}")
    lines.append(f"Google Place ID: {lead.google_place_id or 'Not found'}")
    lines.append(f"Rating: {lead.rating if lead.rating is not None else 'Not found'}")
    lines.append(f"Review Count: {lead.review_count if lead.review_count is not None else 'Not found'}")
    lines.append(f"Business Hours: {lead.business_hours or 'Not found'}")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("OWNER / CONTACT INFORMATION")
    lines.append("--------------------------------")
    lines.append(f"Owner Name: {owner_contact.value if (owner_contact and owner_contact.value) else 'Not found'}")
    lines.append(f"Contact Person: {owner_contact.value if (owner_contact and owner_contact.value) else 'Not found'}")
    lines.append(f"Phone: {phone_contact.value if (phone_contact and phone_contact.value) else 'Not found'}")
    lines.append(f"Email: {email_contact.value if (email_contact and email_contact.value) else 'Not found'}")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("SOCIAL MEDIA")
    lines.append("--------------------------------")
    lines.append(f"Instagram: {instagram.profile_url if instagram else 'Not found'}")
    lines.append(f"Facebook: {facebook.profile_url if facebook else 'Not found'}")
    lines.append(f"YouTube: {youtube.profile_url if youtube else 'Not found'}")
    lines.append(f"LinkedIn: {linkedin.profile_url if linkedin else 'Not found'}")
    other_social_str = ", ".join([s.profile_url for s in other_socials]) if other_socials else 'Not found'
    lines.append(f"Other Social: {other_social_str}")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("GOOGLE / DISCOVERY DATA")
    lines.append("--------------------------------")
    lines.append(f"Scanner Source: {source.source_type if source else 'Not found'}")
    lines.append(f"Search Query: {source.source_query if source else 'Not found'}")
    lines.append(f"Location: {source.source_location if source else 'Not found'}")
    lines.append(f"Discovery Timestamp: {lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else 'Not found'}")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("LEAD SCORING")
    lines.append("--------------------------------")
    lines.append(f"Lead Score: {lead.lead_score}")
    lines.append(f"Opportunity Score: {analysis.overall_score if analysis else 'Not found'}")
    lines.append(f"Priority: {lead.priority or 'Not found'}")
    lines.append(f"Lead Temperature: {qualification.temperature if qualification else 'Not found'}")
    
    if qualification and qualification.qualification_data:
        try:
            data = json.loads(qualification.qualification_data) if isinstance(qualification.qualification_data, str) else qualification.qualification_data
            lines.append(f"Qualification Data: {json.dumps(data)}")
        except Exception:
            lines.append(f"Qualification Data: {qualification.qualification_data}")
    else:
        lines.append("Qualification Data: Not found")
        
    lines.append(f"Reason for Score: {qualification.notes if qualification else 'Not found'}")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("WEBSITE INFORMATION")
    lines.append("--------------------------------")
    if lead.website_url:
        lines.append(f"Website URL: {lead.website_url}")
        lines.append(f"HTTPS: {'Yes' if lead.website_url.startswith('https') else 'No'}")
    else:
        lines.append("No existing website detected.")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("WEBSITE ANALYSIS")
    lines.append("--------------------------------")
    if analysis:
        if analysis.status == 'failed' or analysis.error_message:
            lines.append("Website Status: WEBSITE_UNREACHABLE")
            lines.append(f"Reason: {analysis.error_message or 'Failed to load website.'}")
        elif not analysis.website_exists:
            lines.append("Website Status: NO_WEBSITE")
            lines.append("Reason: No official website URL detected.")
        else:
            lines.append(f"Website Status: {analysis.status.upper()}")
            lines.append(f"Mobile Responsiveness: {analysis.mobile_score if analysis.mobile_score is not None else 'Not found'}")
            lines.append(f"SEO: {analysis.visual_design_score if analysis.visual_design_score is not None else 'Not found'}")
            lines.append(f"Design Quality: {analysis.visual_design_score if analysis.visual_design_score is not None else 'Not found'}")
            lines.append(f"CTA: {analysis.cta_score if analysis.cta_score is not None else 'Not found'}")
            lines.append(f"Booking: {analysis.contact_flow_score if analysis.contact_flow_score is not None else 'Not found'}")
            lines.append(f"Contact Visibility: {analysis.contact_flow_score if analysis.contact_flow_score is not None else 'Not found'}")
            lines.append(f"Opportunity Score: {analysis.overall_score if analysis.overall_score is not None else 'Not found'}")
            lines.append("")
            lines.append("Detailed Findings:")
            lines.append("Observed Facts:")
            for fact in analysis.observed_facts or []:
                lines.append(f"- {fact}")
            lines.append("AI Recommendations:")
            for rec in analysis.ai_recommendations or []:
                lines.append(f"- {rec}")
            lines.append("AI Inferences:")
            for inf in analysis.ai_inferences or []:
                lines.append(f"- {inf}")
    else:
        lines.append("Website Status: Not analyzed")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("PRD INFORMATION")
    lines.append("--------------------------------")
    if prd:
        lines.append(f"PRD Status: {prd.status.upper()}")
        lines.append(f"PRD Version: {prd.current_version}")
        lines.append(f"PRD Created At: {prd.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"PRD Title: {prd.title}")
        lines.append(f"PRD Summary: Goal: {prd.website_goal}, Design: {prd.design_direction}")
    else:
        lines.append("PRD Status: Not found")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("DEMO STATUS")
    lines.append("--------------------------------")
    if demo:
        lines.append(f"Demo URL: {demo.demo_url or 'Not found'}")
        lines.append(f"Demo Status: {'VERIFIED' if demo.url_valid else 'UNVERIFIED'}")
    else:
        lines.append("Demo URL: Not found")
        lines.append("Demo Status: Not found")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("OUTREACH STATUS")
    lines.append("--------------------------------")
    if campaign:
        lines.append(f"Outreach Status: {campaign.status.upper()}")
        lines.append(f"Channel: {campaign.channel.upper()}")
        lines.append(f"Sent At: {campaign.sent_at.strftime('%Y-%m-%d %H:%M:%S') if campaign.sent_at else 'Not found'}")
    else:
        lines.append("Outreach Status: Not found")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("CONVERSATION STATUS")
    lines.append("--------------------------------")
    if conv:
        lines.append(f"Conversation Status: {conv.status.upper()}")
        lines.append(f"Human Takeover Status: {'ON' if conv.status == 'admin_active' else 'OFF'}")
        
        # Latest messages
        history_msgs = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at.desc()).limit(5).all()
        history_msgs.reverse()
        lines.append("")
        lines.append("Recent Customer Messages & AI Replies:")
        for m in history_msgs:
            lines.append(f"[{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {m.sender_type.upper()}: {m.content}")
            if m.detected_intent:
                lines.append(f"  > Intent: {m.detected_intent} (Conf: {m.confidence:.2f}), Stage: {m.sales_stage}")
    else:
        lines.append("Conversation Status: Not found")
        lines.append("Human Takeover Status: OFF")
    lines.append("")
    
    lines.append("--------------------------------")
    lines.append("SYSTEM METADATA")
    lines.append("--------------------------------")
    lines.append(f"Lead ID: LEAD-{lead.id:06d}")
    lines.append(f"Created: {lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else 'Not found'}")
    lines.append(f"Updated: {lead.updated_at.strftime('%Y-%m-%d %H:%M:%S') if lead.updated_at else 'Not found'}")
    lines.append("==================================================")
    lines.append("END OF LEAD DOSSIER")
    lines.append("==================================================")
    
    return "\n".join(lines)


def process_lead_end_to_end(lead_id, force_prd=True):
    """
    Runs the complete automated pipeline for a lead:
    1. Enrich contacts
    2. Website analysis
    3. Re-score
    4. Generate PRD (default status ready)
    5. Generate TXT Dossier
    """
    from app.services.prd_service import generate_lead_prd
    from app.models import Lead, PRD, WebsiteAnalysis, UploadedFile
    from app.extensions import db
    from datetime import datetime, timezone
    import re

    lead = Lead.query.get(lead_id)
    if not lead:
        return {"success": False, "error": "Lead not found."}

    # 1. Contact & Social Enrichment
    try:
        from app.services.pipeline_service import enrich_lead_contacts
        enrich_lead_contacts(lead)
    except Exception as e:
        logger.error(f"Error in lead contact enrichment for {lead.id}: {e}")

    # 2. Website Analysis
    try:
        from app.services.analysis_service import analyze_lead_website
        analyze_lead_website(lead.id)
    except Exception as e:
        logger.error(f"Error in website analysis for {lead.id}: {e}")

    # 3. Lead Re-scoring & Status Synchronization
    try:
        analysis = WebsiteAnalysis.query.filter_by(lead_id=lead.id).first()
        if analysis:
            from app.constants import WebsiteVerdict, LeadStatus
            if analysis.verdict == WebsiteVerdict.NO_WEBSITE:
                lead.lead_score = min(lead.lead_score + 10, 100)
            elif analysis.verdict == WebsiteVerdict.NEEDS_IMPROVEMENT:
                lead.lead_score = min(lead.lead_score + 5, 100)
            
            if analysis.improvement_needed or force_prd:
                lead.status = LeadStatus.WAITING_FOR_DEMO
            else:
                lead.status = LeadStatus.DISQUALIFIED
            db.session.commit()
    except Exception as e:
        logger.error(f"Error in lead scoring/status sync for {lead.id}: {e}")

    # 4. Generate PRD
    try:
        generate_lead_prd(lead.id, force=force_prd)
    except Exception as e:
        logger.error(f"Error in PRD generation for {lead.id}: {e}")

    # 5. Generate TXT Dossier
    try:
        from app.services.pipeline_service import generate_lead_dossier_text
        from app.services.file_service import save_generated_file
        dossier_content = generate_lead_dossier_text(lead)
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', lead.business_name.lower())
        filename = f"LEAD-{lead.id:06d}_{clean_name}.txt"
        
        # Check if dossier already exists and delete
        existing_dossier = UploadedFile.query.filter_by(lead_id=lead.id, file_type='document').filter(UploadedFile.original_filename.like('LEAD-%')).first()
        if existing_dossier:
            db.session.delete(existing_dossier)
            db.session.commit()
            
        save_generated_file(
            file_content=dossier_content,
            original_filename=filename,
            file_type='document',
            lead_id=lead.id
        )
        return {"success": True, "message": "Pipeline completed. Analysis and PRD are ready."}
    except Exception as e:
        logger.error(f"Error generating dossier for {lead.id}: {e}")
        return {"success": False, "error": f"Dossier generation failed: {str(e)}"}
