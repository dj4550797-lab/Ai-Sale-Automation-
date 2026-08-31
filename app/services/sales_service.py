"""
Flixora AI Sales Automation Agent — Sales Pipeline Service

Provides aggregate queries for the visual kanban board and handles deal stage transitions (§52).
"""
from datetime import datetime, timezone
from app.extensions import db
from app.models import SalesDeal, SalesEvent, Lead
from app.constants import PipelineStage, LeadStatus
from app.utils.logger import get_logger

logger = get_logger('services')


def get_deals_by_stage():
    """
    Retrieve all sales deals grouped by pipeline stages for the Kanban dashboard (§52).
    """
    deals = SalesDeal.query.order_by(SalesDeal.updated_at.desc()).all()
    
    # Initialize all columns
    stages_map = {stage: [] for stage in PipelineStage.ALL}
    
    for deal in deals:
        if deal.stage in stages_map:
            stages_map[deal.stage].append(deal)
            
    return stages_map


def update_deal_stage(deal_id, to_stage, deal_value=None, lost_reason=None):
    """
    Transition a sales deal stage, log pipeline event history, and automatically sync the lead status.
    """
    if to_stage not in PipelineStage.ALL:
        return {"success": False, "error": f"Invalid pipeline stage: '{to_stage}'"}

    try:
        deal = SalesDeal.query.get(deal_id)
        if not deal:
            return {"success": False, "error": f"Deal with ID {deal_id} not found."}

        lead = Lead.query.get(deal.lead_id)
        if not lead:
            return {"success": False, "error": "Associated lead not found."}

        old_stage = deal.stage
        deal.stage = to_stage
        
        # Update values
        if deal_value is not None:
            deal.deal_value = float(deal_value)
            deal.final_price = float(deal_value) - (deal.discount_applied or 0)

        # Log won/lost parameters
        if to_stage == PipelineStage.WON:
            deal.won_at = datetime.now(timezone.utc)
            lead.status = LeadStatus.WON
        elif to_stage == PipelineStage.LOST:
            deal.lost_at = datetime.now(timezone.utc)
            deal.lost_reason = lost_reason or 'No reason provided.'
            lead.status = LeadStatus.LOST
        else:
            # Sync standard stages (CONTACTED -> contacted, REPLIED -> replied, INTERESTED -> interested, NEGOTIATION -> negotiation)
            lead.status = to_stage
            
        lead.last_action = f"Pipeline deal transitioned to '{to_stage}'"
        lead.last_action_at = datetime.now(timezone.utc)

        # Register audit event log
        event = SalesEvent(
            deal_id=deal.id,
            event_type='stage_transition',
            from_stage=old_stage,
            to_stage=to_stage,
            details=f"Deal transitioned from {old_stage} to {to_stage}. Lost reason: {lost_reason or 'None'}"
        )
        db.session.add(event)
        
        db.session.commit()
        logger.info(f"Sales deal {deal_id} stage updated from '{old_stage}' to '{to_stage}'")
        return {"success": True, "deal_id": deal.id, "stage": to_stage}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating deal {deal_id} stage: {e}")
        return {"success": False, "error": str(e)}
