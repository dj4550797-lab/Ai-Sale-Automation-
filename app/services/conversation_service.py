"""
Flixora AI Sales Automation Agent — Conversation Service

Manages isolated customer conversations, AI automatic replies, and human takeover workflows (§43, §44, §45, §46, §47, §48).
"""
from datetime import datetime, timezone
from app.extensions import db
from app.models import Lead, Conversation, Message, KnowledgeBase, PricingPlan, Setting
from app.constants import ConversationStatus, LeadStatus, PipelineStage
from app.ai.llm_router import llm_router
from app.utils.logger import get_logger

logger = get_logger('services')


def get_category_settings(category):
    """Local helper to fetch settings by category grouping."""
    rows = Setting.query.filter_by(category=category).all()
    return {row.key: row.value for row in rows}


def create_or_get_conversation(lead_id, channel='email'):
    """
    Fetch an existing conversation session or initialize a new one for a lead (§48).
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return None

    conv = Conversation.query.filter_by(lead_id=lead_id).first()
    if not conv:
        try:
            conv = Conversation(
                lead_id=lead_id,
                channel=channel,
                status=ConversationStatus.AI_ACTIVE
            )
            db.session.add(conv)
            db.session.commit()
            logger.info(f"Initialized new isolated conversation for Lead {lead_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating conversation: {e}")
            return None

    return conv


def add_message(conversation_id, sender_type, content, sender_name=''):
    """
    Append a new message to the isolated conversation history (§48).
    Runs real classification on client messages.
    """
    conv = Conversation.query.get(conversation_id)
    if not conv:
        return None

    try:
        msg = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_name=sender_name or sender_type.upper(),
            content=content,
            status='sent'
        )
        
        # If it's a client message, perform intent and stage classification
        if sender_type == 'client':
            try:
                from app.ai.llm_router import llm_router
                prompt = f"""
                Analyze the following customer message and classify it into one of these intents:
                - greeting
                - price inquiry
                - website inquiry
                - demo inquiry
                - interested
                - not interested
                - objection
                - wants changes
                - wants meeting/call
                - ready to buy
                - follow-up
                - stop/contact removal
                
                Also map the message to one of these sales stages:
                - new
                - contacted
                - replied
                - interested
                - negotiation
                - won
                - lost
                
                Customer message: "{content}"
                """
                schema = {
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string"},
                        "confidence": {"type": "number"},
                        "sales_stage": {"type": "string"}
                    },
                    "required": ["intent", "confidence", "sales_stage"]
                }
                res = llm_router.generate_structured_output(prompt, schema, task_type='intent_classification')
                msg.detected_intent = res.get('intent', 'replied')
                msg.confidence = res.get('confidence', 0.9)
                msg.sales_stage = res.get('sales_stage', 'replied')
                
                # Sync Lead and SalesDeal status
                from app.models import Lead, SalesDeal
                lead = Lead.query.get(conv.lead_id)
                if lead:
                    from app.constants import LeadStatus, PipelineStage
                    stage_map = {
                        'new': LeadStatus.NEW,
                        'contacted': LeadStatus.CONTACTED,
                        'replied': LeadStatus.REPLIED,
                        'interested': LeadStatus.INTERESTED,
                        'negotiation': LeadStatus.NEGOTIATION,
                        'won': LeadStatus.WON,
                        'lost': LeadStatus.LOST
                    }
                    new_status = stage_map.get(msg.sales_stage.lower())
                    if new_status:
                        lead.status = new_status
                        
                    deal = SalesDeal.query.filter_by(lead_id=lead.id).first()
                    if not deal:
                        deal = SalesDeal(lead_id=lead.id, stage=PipelineStage.NEW)
                        db.session.add(deal)
                    deal_stage_map = {
                        'new': PipelineStage.NEW,
                        'contacted': PipelineStage.CONTACTED,
                        'replied': PipelineStage.REPLIED,
                        'interested': PipelineStage.INTERESTED,
                        'negotiation': PipelineStage.NEGOTIATION,
                        'won': PipelineStage.WON,
                        'lost': PipelineStage.LOST
                    }
                    new_deal_stage = deal_stage_map.get(msg.sales_stage.lower())
                    if new_deal_stage:
                        deal.stage = new_deal_stage
            except Exception as classify_err:
                logger.error(f"Error classifying message intent: {classify_err}")

        db.session.add(msg)
        
        # Keep updated_at fresh
        conv.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        return msg
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding message: {e}")
        return None


def generate_chatbot_reply(conversation_id, user_message):
    """
    Compile Agent persona, enabled FAQ rules, and pricing plans to generate a reply using the LLM Router (§46, §47).
    """
    conv = Conversation.query.get(conversation_id)
    if not conv or conv.status != ConversationStatus.AI_ACTIVE:
        # AI replies are paused or taken over by admin (§44)
        logger.info(f"AI response skipped for conversation {conversation_id} (status={conv.status})")
        return None

    lead = Lead.query.get(conv.lead_id)
    if not lead:
        return None

    # 1. Fetch Agent Persona Settings (§47)
    agent_settings = get_category_settings('agent')
    company_settings = get_category_settings('company')

    agent_name = agent_settings.get('agent_name', 'Flixora Assistant')
    agent_role = agent_settings.get('agent_role', 'Sales Representative')
    company_name = company_settings.get('company_name', 'Flixora')
    company_desc = company_settings.get('company_description', 'High-quality website design and development services.')
    tone = agent_settings.get('communication_tone', 'friendly and professional')
    style = agent_settings.get('sales_style', 'consultative')

    # 2. Fetch Knowledge Base Guidelines (§46)
    kb_entries = KnowledgeBase.query.filter_by(is_enabled=True).all()
    kb_text = "\n".join([f"- Title: {kb.title}\n  Content: {kb.content}" for kb in kb_entries])

    # 3. Fetch Pricing Details (§46)
    plans = PricingPlan.query.filter_by(is_enabled=True).all()
    pricing_text = "\n".join([f"- Plan: {p.plan_name}\n  Price: ₹{p.price}\n  Features: {p.features}" for p in plans])

    # 4. Fetch last 10 messages for conversation history (§48)
    history_msgs = Message.query.filter_by(conversation_id=conversation_id)\
        .order_by(Message.created_at.desc()).limit(10).all()
    history_msgs.reverse() # Sort chronologically
    
    history_text = "\n".join([f"{m.sender_type.upper()}: {m.content}" for m in history_msgs])

    prompt = f"""
    You are {agent_name}, working as the {agent_role} at {company_name}.
    Company overview: {company_desc}
    Tone constraints: {tone}. Sales style: {style}.
    
    Company Guidelines & FAQ:
    {kb_text}
    
    Pricing Details:
    {pricing_text}
    
    You are chatting with a prospect from: {lead.business_name} (niche category: {lead.business_category})
    
    Recent Chat Logs:
    {history_text}
    
    Prospect message: {user_message}
    
    Instructions:
    - Respond directly, politely, and concisely to the prospect's question.
    - Rely ONLY on the Company Guidelines & Pricing details provided.
    - If the pricing or answer is not in the text, politely tell them you will check with our design team.
    - Do NOT fabricate names or personal identities.
    - Do NOT invent discounts or prices.
    - Return only the raw message text. Do not wrap in markdown blocks.
    """

    try:
        reply_content = llm_router.generate_text(prompt, task_type='client_chat').strip()
        # Save AI reply message
        ai_msg = add_message(conversation_id, 'ai', reply_content, sender_name=agent_name)
        return ai_msg
    except Exception as e:
        logger.error(f"Error generating chatbot reply: {e}")
        return None


def toggle_takeover_status(conversation_id, active, admin_user_id):
    """
    Activate/Deactivate Human Takeover, toggling the AI responder status (§45).
    """
    conv = Conversation.query.get(conversation_id)
    if not conv:
        return {"success": False, "error": "Conversation not found."}

    try:
        if active:
            conv.status = ConversationStatus.ADMIN_ACTIVE
            conv.taken_over_by = admin_user_id
            conv.taken_over_at = datetime.now(timezone.utc)
            logger.info(f"Admin taken over control of Conversation {conversation_id}")
        else:
            conv.status = ConversationStatus.AI_ACTIVE
            conv.taken_over_by = None
            conv.taken_over_at = None
            logger.info(f"AI assistant reactivated for Conversation {conversation_id}")

        db.session.commit()
        return {"success": True, "status": conv.status}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling takeover status: {e}")
        return {"success": False, "error": str(e)}
