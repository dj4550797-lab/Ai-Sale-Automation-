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
                if any(w in c for w in ['wrong number', 'wrong person', 'galat number', 'galti se', 'not my business', 'not the owner', 'remove me', 'wrong no', 'galat no', 'remove my number', 'mera number hatao']):
                    detected_intent, detected_stage = 'wrong_number', 'lost'
                elif any(w in c for w in ['who are you', 'tu kon ho', 'kaun ho', 'kon ho', 'aap kaun', 'kiske liye', 'kis ke liye', 'who r u', 'kya kaam']):
                    detected_intent, detected_stage = 'identity_inquiry', 'replied'
                elif any(w in c for w in ['human', 'insaan', 'real person', 'manager', 'owner', 'talk to person', 'agent se baat', 'baat karvao', 'call me', 'call karo', 'phone karo']):
                    detected_intent, detected_stage = 'human_escalation', 'interested'
                elif any(w in c for w in ['price', 'prize', 'cost', 'how much', 'rate', 'package', 'pricing', 'charges', 'charge', 'kya rate', 'kitna', 'kharcha']):
                    detected_intent, detected_stage = 'price inquiry', 'interested'
                elif any(w in c for w in ['nice', 'good', 'mast', 'badhiya', 'great', 'awesome', 'sahi hai', 'pasand aaya', 'loved it', 'beautiful']):
                    detected_intent, detected_stage = 'positive_feedback', 'interested'
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
                    if detected_intent == 'wrong_number':
                        lead.status = LeadStatus.DISQUALIFIED
                    else:
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
    Compile Agent persona, company settings, enabled FAQ rules, and pricing plans to generate a reply using LLM Router (§46, §47).
    Enforces strict anti-spam for demo links and human sales persona.
    """
    conv = Conversation.query.get(conversation_id)
    if not conv or conv.status != ConversationStatus.AI_ACTIVE:
        # AI replies are paused or taken over by admin (§44)
        logger.info(f"AI response skipped for conversation {conversation_id} (status={getattr(conv, 'status', None)})")
        return None

    lead = Lead.query.get(conv.lead_id)
    if not lead:
        return None

    user_lower = (user_message or '').lower().strip()

    # 1. Immediate Opt-Out, Rejection & Stop Condition (§51, Anti-Spam)
    rejection_keywords = [
        'deal cancel', 'cancel deal', 'cancel kar', 'cancel kr', 'cancel',
        'not interested', 'nahi chahiye', 'nahi lena', 'nahi interested', 'mat bhejo',
        'dont message', "don't message", 'stop messaging', 'stop message', 'message mat',
        'reply mat', 'mat de', 'block kar', 'block kr', 'police', '100 ko call', 'call kiya',
        'fraud', 'scam', 'cheating', 'gandu', 'sala', 'harami', 'chirkut', 'complaint'
    ]
    is_opt_out = any(k in user_lower for k in rejection_keywords)
    if is_opt_out:
        # Permanently stop AI for this lead so it never spams or argues
        conv.status = ConversationStatus.ADMIN_ACTIVE
        if lead:
            lead.status = LeadStatus.DISQUALIFIED
        reply_content = (
            "Understood sir. Humne aapki request note kar li hai aur future me aapko koi message nahi aayega. "
            "Inconvenience ke liye sincere apologies. Wishing you all the best."
        )
        ai_msg = add_message(conversation_id, 'ai', reply_content, sender_name="Support Team")
        db.session.commit()
        logger.info(f"Conversation {conv.id} stopped permanently after rejection/opt-out keyword.")
        return ai_msg

    # 2. Fetch Company & Agent Persona Settings (§47, §93, §94)
    agent_settings = get_category_settings('agent')
    company_settings = get_category_settings('company')

    company_name = company_settings.get('company_name') or 'Flixora Web Solutions'
    company_desc = company_settings.get('company_description') or 'Professional web design and e-commerce development agency.'
    company_location = company_settings.get('business_location') or 'Delhi, India'
    company_phone = company_settings.get('business_phone') or '+91 8793393102'
    company_email = company_settings.get('business_email') or 'sales@flixora.com'
    company_website = company_settings.get('website') or 'https://flixora.com'

    agent_name = agent_settings.get('agent_name') or 'Sales Team'
    if agent_name.lower().endswith(' ai') or agent_name.lower() == 'ai':
        agent_name = agent_name.replace(' AI', ' Team').replace(' ai', ' Team').strip()
    agent_role = agent_settings.get('agent_role') or 'Design & Growth Consultant'
    tone = agent_settings.get('communication_tone') or 'Professional, polite, and consultative'
    sales_style = agent_settings.get('sales_style') or 'consultative'
    allowed_info = agent_settings.get('allowed_information', '')
    restricted_info = agent_settings.get('restricted_information', '')

    # 3. Fetch Knowledge Base Guidelines & Pricing Details (§46)
    kb_entries = KnowledgeBase.query.filter_by(is_enabled=True).all()
    kb_text = "\n".join([f"- Title: {kb.title}\n  Content: {kb.content}" for kb in kb_entries])

    plans = PricingPlan.query.filter_by(is_enabled=True).all()
    pricing_text = "\n".join([f"- Plan: {p.plan_name}\n  Price: ₹{p.price}\n  Features: {p.features}" for p in plans])

    # 4. Resolve Demo URL (Always Full Absolute URL)
    from app.models import DemoProject
    demo = (lead.demos.first() if hasattr(lead, 'demos') else None) or DemoProject.query.filter_by(lead_id=lead.id).first()
    base_domain = "https://ai-sale-automation.onrender.com"
    demo_url = demo.demo_url if (demo and demo.demo_url) else f"/demos/preview/{lead.id}"
    if not demo_url.startswith('http'):
        demo_url = f"{base_domain}{demo_url if demo_url.startswith('/') else '/' + demo_url}"

    # 5. Fetch Message History & Anti-Spam Demo Link Tracking
    history_msgs = Message.query.filter_by(conversation_id=conversation_id)\
        .order_by(Message.created_at.desc()).limit(12).all()
    history_msgs.reverse()

    demo_already_sent = any((demo_url in (m.content or '') or '/demos/preview/' in (m.content or '')) for m in history_msgs)
    wants_demo = any(w in user_lower for w in [
        'demo', 'sample', 'link', 'preview', 'portfolio', 'site', 'dikhao', 'bhejo', 'dekho', 'design dikhao'
    ])
    is_ai_inquiry = any(w in user_lower for w in [
        'tum ai ho', 'tu ai hai', 'tu ai ha', 'you are ai', 'u are ai', 'ur ai', 
        'are you ai', 'ai ho kya', 'bot ho', 'robot ho', 'machine ho'
    ])
    is_company_inquiry = any(w in user_lower for w in [
        'kahan par hai', 'kahan hai', 'kider ha', 'kider', 'location', 'office', 'address',
        'company name', 'phone number', 'contact number', 'manager number', 'name bol', 'naam bol'
    ])

    history_text = "\n".join([f"{m.sender_type.upper()}: {m.content}" for m in history_msgs])

    prompt = f"""
    You are {agent_name}, working as a human {agent_role} at {company_name}.
    Company Overview: {company_desc}
    Office Location: {company_location}
    Official Phone / Support Contact: {company_phone}
    Official Email: {company_email}
    Official Website: {company_website}
    Tone: {tone}. Sales style: {sales_style}.
    
    Lead Details:
    - Business: {lead.business_name} (Category: {lead.business_category}, City: {lead.city or company_location})
    
    STRICT DEMO LINK RULES:
    - Personalized Demo Link: {demo_url}
    - Has demo link already been shared previously: {'YES' if demo_already_sent else 'NO'}
    - Did customer specifically ask for demo/link in this message: {'YES' if wants_demo else 'NO'}
    - CRITICAL ANTI-SPAM RULE:
      * If demo link was already shared previously (YES) and customer DID NOT ask for the link (NO), DO NOT include {demo_url} in your reply!
      * Never repeat or paste the demo link in multiple messages. It feels like robotic spam. Only send the link if they explicitly ask for it!
    
    STRICT HUMAN IDENTITY & COMPANY RULES:
    - ABSOLUTE PROHIBITION: NEVER state or admit "I am an AI", "Main AI hoon", "I am a bot/machine".
    - If customer asks "Tum AI ho?", "Are you AI?": Politely clarify that you are {agent_name} from {company_name}'s web development & design team, coordinating with designers to build their official online site.
    - If customer asks about company location, address, or contact number: Give the exact details: Location is {company_location}, Official Contact is {company_phone}. Never be evasive or claim you don't know your manager's name.
    {f"- Specific Restricted Directives: {restricted_info}" if restricted_info else ""}
    {f"- Authorized Topics to Share: {allowed_info}" if allowed_info else ""}
    
    Pricing Details (Only share if customer asks about price or package):
    {pricing_text}
    
    Recent Chat Logs:
    {history_text}
    
    Customer message: {user_message}
    
    RESPONSE GUIDELINES:
    - Respond in friendly, polite Hinglish if customer writes in Hinglish/Hindi, or in English if they write in English.
    - Keep answers short and natural (2-3 sentences), ideal for WhatsApp.
    - If customer asks for human manager or call: Confirm our manager will connect with them on this phone number shortly, and ask what time is convenient.
    - Do NOT wrap in markdown code fences. Return only raw text.
    """

    try:
        reply_content = llm_router.generate_text(prompt, task_type='client_chat').strip()
        # Enforce no demo link if already sent and not requested
        if demo_already_sent and not wants_demo and demo_url in reply_content:
            reply_content = reply_content.replace(demo_url, "").strip()
            reply_content = reply_content.replace("Aap apna personalized demo yahan dekh sakte hain:", "").replace("demo yahan hai:", "").strip()
        # Enforce no "AI hoon" leak
        if "main ai hoon" in reply_content.lower() or "i am an ai" in reply_content.lower():
            reply_content = f"Nahi sir! Main {agent_name} hoon, {company_name} ki web development team se! Hum local businesses ke liye modern websites aur digital presence design karte hain. Aapko website ya pricing ke baare mein koi doubt ho toh please batayein."
        ai_msg = add_message(conversation_id, 'ai', reply_content, sender_name=agent_name)
    except Exception as e:
        logger.warning(f"Error generating chatbot reply via LLM ({e}). Using intelligent sales responder.")
        if is_ai_inquiry:
            reply_content = f"Nahi sir! Main {agent_name} hoon, {company_name} ki development aur design team se! Hum real developers aur designers ki team hain jo local businesses ke liye high-converting websites banate hain. Aapko designs ya packages ke baare mein koi doubt ho toh please batayein, main clear kar deta hoon. 😊"
        elif is_company_inquiry:
            reply_content = f"Sir, hamari company ka naam {company_name} hai. Hamara head office {company_location} mein sthit hai, aur hamara official contact number {company_phone} hai. Aap humein {company_email} par bhi reach out kar sakte hain."
        elif any(w in user_lower for w in ['wrong number', 'wrong person', 'galat number', 'galti se', 'not my business', 'not the owner', 'remove me', 'wrong no', 'galat no', 'remove my number', 'mera number hatao']):
            reply_content = "माफ़ी चाहते हैं! 🙏 लगता है हमारे पास ग़लत नंबर दर्ज हो गया था। हमने अपने सिस्टम से आपका नंबर तुरंत रिमूव कर दिया है ताकि आपको दोबारा कोई मैसेज न आए। आपका दिन शुभ हो!"
        elif any(w in user_lower for w in ['human', 'insaan', 'real person', 'manager', 'owner', 'talk to person', 'agent se baat', 'baat karvao', 'call me', 'call karo', 'phone karo']):
            reply_content = f"जी बिल्कुल! 🙏 मैंने हमारी सीनियर टीम को नोटिफ़ाई कर दिया है। हमारे सेल्स मैनेजर आपसे थोड़ी देर में इसी नंबर पर या official number {company_phone} से कॉल/WhatsApp पर कनेक्ट करेंगे। क्या अभी बात करने का सही समय है?"
        elif any(w in user_lower for w in ['price', 'prize', 'cost', 'rate', 'how much', 'pricing', 'charges', 'kitna', 'rate kya', 'kharcha']):
            reply_content = f"हमारे पास {lead.business_name} के लिए 3 बेहतरीन packages हैं:\n- Starter Showcase: ₹14,999 (1-page fast website, WhatsApp CTA & 1yr hosting)\n- Growth Business Engine: ₹24,999 (Multi-section funnel, booking flow & Local SEO)\n- Enterprise Custom App: ₹44,999 (Custom database, payment gateway & admin dashboard)\n\nआप अपनी आवश्यकता के अनुसार कौन सा plan पसंद करेंगे? 😊"
        elif any(w in user_lower for w in ['nice', 'good', 'mast', 'badhiya', 'great', 'awesome', 'sahi hai', 'pasand aaya', 'loved it', 'beautiful']):
            reply_content = f"Thank you so much! 😊 बहुत खुशी हुई कि आपको design पसंद आया! क्या आप हमारे pricing packages देखना चाहेंगे ताकि हम इसे आपके official domain पर live launch कर सकें?"
        elif wants_demo:
            reply_content = f"You can preview your live prototype concept right here: {demo_url} 🚀 Let me know if you would like any adjustments to the branding or menu!"
        elif any(w in user_lower for w in ['yes', 'interested', 'sure', 'ok', 'call', 'talk', 'meeting', 'baat']):
            reply_content = f"That sounds great! I can arrange a quick 5-minute call or WhatsApp consultation for {lead.business_name}. What is the best time today?"
        else:
            if not demo_already_sent:
                reply_content = f"Thank you for getting back to us! We crafted a live prototype concept for {lead.business_name} here: {demo_url}. Feel free to ask any questions about features or packages!"
            else:
                reply_content = f"Thank you for getting back to us! Feel free to ask any questions about features, domain hosting, or our packages for {lead.business_name}. How can I assist you today?"
        ai_msg = add_message(conversation_id, 'ai', reply_content, sender_name=agent_name)

    # Post-reply state transition (Wrong Number / Human Handover)
    try:
        if any(w in user_lower for w in ['wrong number', 'wrong person', 'galat number', 'galti se', 'not my business', 'not the owner', 'remove me', 'wrong no', 'galat no', 'remove my number', 'mera number hatao']):
            conv.status = ConversationStatus.ADMIN_ACTIVE
            if lead:
                lead.status = LeadStatus.DISQUALIFIED
            db.session.commit()
            logger.info(f"Conversation {conv.id} marked ADMIN_ACTIVE and lead disqualified after wrong number reply.")
        elif any(w in user_lower for w in ['human', 'insaan', 'real person', 'manager', 'owner', 'talk to person', 'agent se baat', 'baat karvao', 'call me', 'call karo', 'phone karo']):
            conv.status = ConversationStatus.ADMIN_ACTIVE
            db.session.commit()
            logger.info(f"Conversation {conv.id} marked ADMIN_ACTIVE after human escalation handover.")
    except Exception as state_err:
        logger.error(f"Error updating conversation state post-reply: {state_err}")

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
