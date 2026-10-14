"""
Flixora AI Sales Automation Agent — Follow-Up Scheduler Service

Manages delay periods, followup counts, message templates, and stop conditions (§49, §50, §51).
"""
from datetime import datetime, timezone, timedelta
from flask import current_app
from app.extensions import db
from app.models import Lead, FollowUp, OutreachCampaign, OutreachEvent, DemoProject
from app.constants import FollowUpStatus, LeadStatus, OutreachStatus
from app.ai.llm_router import llm_router
from app.utils.logger import get_logger

logger = get_logger('services')

# Default configurations
MAX_FOLLOWUPS = 2
DELAY_DAYS = 3


def schedule_next_followup(lead_id, outreach_id, followup_number=1, delay_days=DELAY_DAYS):
    """
    Schedule a new follow-up attempt in the database.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return {"success": False, "error": "Lead not found."}

    # Verify campaign exists
    campaign = OutreachCampaign.query.get(outreach_id)
    if not campaign:
        return {"success": False, "error": "Associated outreach campaign not found."}

    scheduled_time = datetime.now(timezone.utc) + timedelta(days=delay_days)
    
    try:
        followup = FollowUp(
            lead_id=lead_id,
            outreach_id=outreach_id,
            followup_number=followup_number,
            channel=campaign.channel,
            status=FollowUpStatus.SCHEDULED,
            scheduled_at=scheduled_time
        )
        db.session.add(followup)
        db.session.commit()
        logger.info(f"Follow-up #{followup_number} scheduled for Lead {lead_id} at {scheduled_time}")
        return {"success": True, "followup_id": followup.id}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error scheduling follow-up: {e}")
        return {"success": False, "error": str(e)}


def process_followups_cron():
    """
    Scan scheduled follow-ups, validate stop conditions, compile follow-up text, and execute sending (§50, §51).
    """
    now = datetime.now(timezone.utc)
    # Find all scheduled follow-ups due
    due_followups = FollowUp.query.filter(
        FollowUp.status == FollowUpStatus.SCHEDULED,
        FollowUp.scheduled_at <= now
    ).all()

    logger.info(f"Cron follow-up scanning: found {len(due_followups)} items due.")
    
    processed_count = 0
    cancelled_count = 0

    for fup in due_followups:
        lead = Lead.query.get(fup.lead_id)
        campaign = OutreachCampaign.query.get(fup.outreach_id)

        if not lead or not campaign:
            fup.status = FollowUpStatus.CANCELLED
            fup.stop_reason = "Missing database relations."
            continue

        # ── Check Stop Conditions (§51) ──
        # Cancel follow-ups if prospect replied, paused, won, lost or disqualified
        stop_statuses = [
            LeadStatus.REPLIED,
            LeadStatus.INTERESTED,
            LeadStatus.NEGOTIATION,
            LeadStatus.WON,
            LeadStatus.LOST,
            LeadStatus.PAUSED,
            LeadStatus.DISQUALIFIED
        ]

        if lead.status in stop_statuses:
            fup.status = FollowUpStatus.CANCELLED
            fup.stop_reason = f"Stop condition met: Lead status is '{lead.status}'."
            cancelled_count += 1
            db.session.commit()
            continue

        # Fetch demo project preview link
        demo = DemoProject.query.filter_by(lead_id=lead.id).first()
        demo_url = demo.demo_url if demo else 'the demo link'

        # ── Compile Follow-Up Message ──
        prompt = f"""
        You are a polite business representative following up with a prospect:
        Business Name: {lead.business_name}
        Original outreach sent via {fup.channel}.
        
        Write a extremely brief, gentle follow-up reminder (1-2 sentences).
        Ask if they had a chance to check the website preview demo: {demo_url}
        Do not make false claims or fabricate pressure. Keep it professional.
        Return only the raw message text. Do not wrap in quotes or markdown.
        """

        try:
            followup_text = llm_router.generate_text(prompt, task_type='followup_compile').strip()
            
            # Save message content
            fup.message_content = followup_text
            fup.sent_at = datetime.now(timezone.utc)
            fup.status = FollowUpStatus.SENT

            # Log outreach event tracker
            evt = OutreachEvent(
                campaign_id=campaign.id,
                event_type='sent',
                details=f"Follow-up #{fup.followup_number} sent: '{followup_text}'"
            )
            db.session.add(evt)

            # Update campaign status
            campaign.updated_at = datetime.now(timezone.utc)

            # ── Schedule Next Follow-up or Stop ──
            if fup.followup_number < MAX_FOLLOWUPS:
                # Schedule next iteration (e.g. Follow-Up 2)
                schedule_next_followup(
                    lead_id=lead.id,
                    outreach_id=campaign.id,
                    followup_number=fup.followup_number + 1,
                    delay_days=DELAY_DAYS
                )
            else:
                # Stop follow-ups sequence (max iterations reached)
                campaign.status = OutreachStatus.STOPPED
                logger.info(f"Max followups reached for Lead {lead.id}. Stopped further sequence.")

            db.session.commit()
            processed_count += 1
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing follow-up ID {fup.id}: {e}")

    return {
        "success": True,
        "processed": processed_count,
        "cancelled": cancelled_count
    }
