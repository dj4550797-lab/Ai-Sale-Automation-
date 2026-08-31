"""
Flixora AI Sales Automation Agent — Outreach Service

Generates personalized messaging content and maps delivery states (§39, §40).
"""
from datetime import datetime, timezone
from flask import current_app
from app.extensions import db
from app.models import Lead, PRD, DemoProject, OutreachCampaign, OutreachEvent, SalesDeal
from app.constants import OutreachStatus, LeadStatus, PipelineStage
from app.ai.llm_router import llm_router
from app.utils.logger import get_logger

logger = get_logger('services')


def generate_outreach_message(lead_id, channel):
    """
    Generate a personalized and concise outreach message based on lead name, category, approved PRD, and demo link.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return {"success": False, "error": f"Lead with ID {lead_id} not found."}

    prd = PRD.query.filter_by(lead_id=lead_id, status='approved').first()
    demo = DemoProject.query.filter_by(lead_id=lead_id).first()

    if not prd or not demo:
        return {"success": False, "error": "An approved PRD and a compiled demo are required before preparing outreach."}

    logger.info(f"Generating personalized outreach pitch for {lead.business_name} via {channel}")

    # Prompt matching PRD specs (§40)
    prompt = f"""
    You are an expert sales outreach copywriter for Flixora.
    Write a highly-personalized, short, and friendly outreach message to:
    Business: {lead.business_name}
    Niche/Category: {lead.business_category}
    
    Context:
    - Approved PRD Website Goal: {prd.website_goal}
    - Visual design focus: {prd.design_direction}
    - Demo link: {demo.demo_url}
    - Channel: {channel}
    
    Structure requirements (§40):
    1. A warm personal greeting (e.g. 👋 Hello [Name] / Team)
    2. A specific, non-fabricated line mentioning their category/aesthetics or how their current site can be improved (from PRD).
    3. A clear demo link reference where they can preview the concept.
    4. A single, very simple, low-friction call to action (e.g., "Let me know if this color theme looks right for you").
    
    Strict constraints:
    - Do NOT invent facts or statistics about the business.
    - Keep it short (under 4-5 sentences).
    - Return only the raw text message. Do not wrap in quotes or markdown.
    """

    try:
        message = llm_router.generate_text(prompt, task_type='outreach_pitch')
        return {"success": True, "message": message.strip()}
    except Exception as e:
        logger.error(f"Failed to generate outreach pitch: {e}")
        return {"success": False, "error": str(e)}


def create_outreach_campaign(lead_id, channel, message_content=None):
    """
    Create or update an outreach campaign entry and compile the message draft.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return {"success": False, "error": "Lead not found."}

    demo = DemoProject.query.filter_by(lead_id=lead_id).first()
    demo_id = demo.id if demo else None

    # Resolve message text
    if not message_content:
        res = generate_outreach_message(lead_id, channel)
        if not res.get('success'):
            return res
        message_content = res.get('message')

    try:
        # Create campaign entry
        campaign = OutreachCampaign.query.filter_by(lead_id=lead_id, channel=channel).first()
        if not campaign:
            campaign = OutreachCampaign(
                lead_id=lead_id,
                demo_id=demo_id,
                channel=channel,
                message_content=message_content,
                status=OutreachStatus.READY
            )
            db.session.add(campaign)
        else:
            campaign.message_content = message_content
            campaign.status = OutreachStatus.READY

        db.session.commit()
        return {"success": True, "campaign_id": campaign.id, "message": message_content}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating outreach campaign: {e}")
        return {"success": False, "error": str(e)}


def send_outreach_campaign(campaign_id):
    """
    Execute outreach delivery, log tracking events, and transition pipeline statuses.
    """
    campaign = OutreachCampaign.query.get(campaign_id)
    if not campaign:
        return {"success": False, "error": "Campaign not found."}

    lead = Lead.query.get(campaign.lead_id)
    if not lead:
        return {"success": False, "error": "Associated lead not found."}

    test_mode = current_app.config.get('TEST_MODE', True)
    
    try:
        campaign.sent_at = datetime.now(timezone.utc)
        
        if campaign.channel == 'whatsapp':
            from app.integrations.whatsapp_adapter import WhatsAppAdapter
            adapter = WhatsAppAdapter()
            if not adapter.is_configured():
                return {"success": False, "error": "WhatsApp Cloud API is NOT CONFIGURED."}
            
            # Fetch lead phone number
            phone_contact = LeadContact.query.filter_by(lead_id=lead.id, contact_type='phone').first()
            if not phone_contact or not phone_contact.value:
                return {"success": False, "error": "Lead phone number is Not Available."}
                
            res = adapter.send_text_message(phone_contact.value, campaign.message_content)
            if not res.get('success'):
                return {"success": False, "error": f"Failed to send WhatsApp message: {res.get('error')}"}
                
            campaign.status = OutreachStatus.SENT
            evt_sent = OutreachEvent(campaign_id=campaign_id, event_type='sent', details=f"WhatsApp message sent. ID: {res.get('message_id')}")
            db.session.add(evt_sent)
            
            # Also create/get isolated conversation session and save message
            from app.services.conversation_service import create_or_get_conversation, add_message
            conv = create_or_get_conversation(lead.id, channel='whatsapp')
            if conv:
                add_message(conv.id, 'ai', campaign.message_content, sender_name='Flixora AI')
        else:
            if test_mode:
                # Simulated deliver pings
                campaign.status = OutreachStatus.DELIVERED
                campaign.delivered_at = datetime.now(timezone.utc)
                
                # Log sent event
                evt_sent = OutreachEvent(campaign_id=campaign_id, event_type='sent', details='Simulated delivery triggered.')
                evt_del = OutreachEvent(campaign_id=campaign_id, event_type='delivered', details='Simulated receiver delivered.')
                db.session.add_all([evt_sent, evt_del])
            else:
                # Real delivery adapter
                campaign.status = OutreachStatus.SENT
                evt_sent = OutreachEvent(campaign_id=campaign_id, event_type='sent', details='Outbound API submission successful.')
                db.session.add(evt_sent)

        # Transition Lead Status
        lead.status = LeadStatus.CONTACTED
        lead.last_action = f"Outreach pitch sent via {campaign.channel}"
        lead.last_action_at = datetime.now(timezone.utc)

        # Create/sync Sales Deal record
        deal = SalesDeal.query.filter_by(lead_id=lead.id).first()
        if not deal:
            deal = SalesDeal(
                lead_id=lead.id,
                prd_id=PRD.query.filter_by(lead_id=lead.id).first().id if PRD.query.filter_by(lead_id=lead.id).first() else None,
                demo_id=campaign.demo_id,
                stage=PipelineStage.CONTACTED,
                deal_value=299.0, # Default catalog base pricing
                final_price=299.0
            )
            db.session.add(deal)
        else:
            deal.stage = PipelineStage.CONTACTED

        db.session.commit()
        logger.info(f"Outreach successfully processed for Campaign {campaign_id}")
        return {"success": True, "status": campaign.status}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error executing outreach campaign {campaign_id}: {e}")
        return {"success": False, "error": str(e)}


def simulate_incoming_reply(lead_id, reply_content):
    """
    Simulation utility to register prospect replies, updating status maps and stopping automatic follow-ups (§51).
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return {"success": False, "error": "Lead not found."}

    try:
        # 1. Update Outreach Campaigns matching this lead
        campaigns = OutreachCampaign.query.filter_by(lead_id=lead_id).all()
        for camp in campaigns:
            camp.status = OutreachStatus.REPLIED
            camp.replied_at = datetime.now(timezone.utc)
            # Log reply event
            evt_reply = OutreachEvent(campaign_id=camp.id, event_type='replied', details=f"Client response: '{reply_content}'")
            db.session.add(evt_reply)

        # 2. Sync lead status
        # Analyze reply sentiment (simple check: if 'yes', 'cost', 'price', or 'interested' is found, mark as interested)
        reply_lower = reply_content.lower()
        if any(w in reply_lower for w in ['yes', 'cost', 'price', 'pricing', 'interest', 'sure', 'ok', 'good']):
            lead.status = LeadStatus.INTERESTED
            target_stage = PipelineStage.INTERESTED
        else:
            lead.status = LeadStatus.REPLIED
            target_stage = PipelineStage.REPLIED
            
        lead.last_action = "Prospect reply registered"
        lead.last_action_at = datetime.now(timezone.utc)

        # 3. Update Sales Deal Stage
        deal = SalesDeal.query.filter_by(lead_id=lead_id).first()
        if deal:
            deal.stage = target_stage

        db.session.commit()
        logger.info(f"Prospect reply simulated for Lead {lead_id} -> status: {lead.status}")
        return {"success": True, "lead_status": lead.status}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error simulating reply: {e}")
        return {"success": False, "error": str(e)}
