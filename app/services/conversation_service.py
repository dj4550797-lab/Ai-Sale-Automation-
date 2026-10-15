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
        
        # If it's a client message, perform fast intent and stage classification
        if sender_type == 'client':
            try:
                c = (content or '').lower().strip()
                if any(w in c for w in ['price', 'cost', 'how much', 'rate', 'package', 'pricing', 'charges', 'charge', 'kya rate', 'kitna']):
                    detected_intent, detected_stage = 'price inquiry', 'interested'
                elif any(w in c for w in ['demo', 'sample', 'link', 'preview', 'portfolio', 'website', 'site', 'dikhao', 'design']):
                    detected_intent, detected_stage = 'demo inquiry', 'interested'
                elif any(w in c for w in ['hi', 'hello', 'hey', 'namaste', 'halo', 'good morning', 'good evening']):
                    detected_intent, detected_stage = 'greeting', 'replied'
                elif any(w in c for w in ['call', 'talk', 'meet', 'phone', 'contact', 'baat', 'timing']):
                    detected_intent, detected_stage = 'wants meeting/call', 'interested'
                elif any(w in c for w in ['yes', 'sure', 'interested', 'ready', 'okay', 'ha', 'haan', 'done']):
                    detected_intent, detected_stage = 'interested', 'interested'
                elif any(w in c for w in ['no', 'not interested', 'nahi', 'stop', 'remove', 'unsubscribe']):
                    detected_intent, detected_stage = 'not interested', 'lost'
                elif any(w in c for w in ['change', 'modify', 'custom', 'food', 'menu', 'color', 'theme']):
                    detected_intent, detected_stage = 'wants changes', 'negotiation'
                else:
                    detected_intent, detected_stage = 'inquiry', 'replied'

                msg.detected_intent = detected_intent
                msg.confidence = 0.95
                msg.sales_stage = detected_stage
                
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

    # 4. Fetch personalized demo URL for this lead
    from app.models import DemoProject
    demo = (lead.demos.first() if hasattr(lead, 'demos') else None) or DemoProject.query.filter_by(lead_id=lead.id).first()
    demo_url = demo.demo_url if (demo and demo.demo_url) else f"https://ai-sale-automation.onrender.com/demos/preview/{lead.id}"
    if demo_url.startswith('/'):
        demo_url = f"https://ai-sale-automation.onrender.com{demo_url}"

    # 5. Fetch last 10 messages for conversation history (§48)
    history_msgs = Message.query.filter_by(conversation_id=conversation_id)\
        .order_by(Message.created_at.desc()).limit(10).all()
    history_msgs.reverse() # Sort chronologically
    
    history_text = "\n".join([f"{m.sender_type.upper()}: {m.content}" for m in history_msgs])

    prompt = f"""
    You are {agent_name}, working as the {agent_role} at {company_name}.
    Company overview: {company_desc}
    Tone constraints: {tone}. Sales style: {style}.
    
    Lead Details:
    - Business: {lead.business_name} (Category: {lead.business_category}, City: {lead.city or 'India'})
    - Personalized Live Interactive Demo Website Link: {demo_url}
    
    Company Guidelines & FAQ:
    {kb_text}
    
    Pricing Details:
    {pricing_text}
    
    Recent Chat Logs:
    {history_text}
    
    Prospect message: {user_message}
    
    CRITICAL Instructions:
    - Respond directly, politely, warmly, and concisely to the prospect's question.
    - When the prospect asks for their website link, demo, prototype, portfolio, or preview (e.g. "demo link bhejo", "link send karo", "sample dikhao", "show demo"), ALWAYS give them their live interactive link: {demo_url}. Inform them warmly that their interactive prototype has ALREADY BEEN BUILT and is live for them to explore! NEVER say you will check with the design team for their demo link.
    - If they ask about pricing, concisely present our clear packages (Starter Showcase: ₹14,999, Growth Business Engine: ₹24,999, Enterprise Custom App: ₹44,999).
    - If the user messages in Hindi or Hinglish, answer in friendly and polite Hinglish.
    - Keep replies concise (2-4 lines/bullets), ideal for WhatsApp reading.
    - Do NOT fabricate fake personal names or discounts.
    - Return only the raw message text. Do not wrap in markdown code blocks.
    """

    try:
        reply_content = llm_router.generate_text(prompt, task_type='client_chat').strip()
        # Save AI reply message
        ai_msg = add_message(conversation_id, 'ai', reply_content, sender_name=agent_name)
        return ai_msg
    except Exception as e:
        logger.warning(f"Error generating chatbot reply via LLM ({e}). Using intelligent sales responder.")
        user_lower = user_message.lower()
        if any(w in user_lower for w in ['price', 'cost', 'rate', 'how much', 'pricing', 'charges', 'kitna', 'rate kya']):
            reply_content = f"Hello! Our website design packages start from ₹14,999 (Starter Showcase) to ₹24,999 (Growth Business Engine), including mobile responsive UI, SSL security, custom domain, and WhatsApp booking integration. Would you like us to customize this for {lead.business_name}?"
        elif any(w in user_lower for w in ['demo', 'link', 'sample', 'preview', 'portfolio', 'site', 'bhejo', 'dikhao']):
            reply_content = f"You can preview your live prototype concept right here: {demo_url} 🚀 Let me know if you would like any adjustments to the branding or menu!"
        elif any(w in user_lower for w in ['yes', 'interested', 'sure', 'ok', 'call', 'talk', 'meeting', 'baat']):
            reply_content = f"That sounds great! I can arrange a quick 5-minute call or WhatsApp consultation for {lead.business_name}. What is the best time today?"
        else:
            reply_content = f"Thank you for getting back to us! We crafted a live prototype concept for {lead.business_name} here: {demo_url}. Feel free to ask any questions about features or packages!"
        ai_msg = add_message(conversation_id, 'ai', reply_content, sender_name=agent_name)
        return ai_msg


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
