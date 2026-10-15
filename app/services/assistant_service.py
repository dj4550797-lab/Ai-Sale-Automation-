"""
Flixora AI Sales Automation Agent — Admin AI Assistant Service

Dispatches queries, queries database tools (leads, PRDs, knowledge base, system health),
and supports multimodal image analysis (vision).
"""
import os
import base64
import mimetypes
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from flask import current_app

from app.extensions import db
from app.models import (
    Lead, PRD, Conversation, Message, PricingPlan,
    AutomationJob, LLMProvider, User, KnowledgeBase
)
from app.constants import PRDStatus, LeadStatus, ProviderStatus
from app.ai.llm_router import llm_router
from app.utils.logger import get_logger

logger = get_logger('services')


class AssistantIntentSchema(BaseModel):
    """Pydantic schema for parsing user intent/tool selection."""
    tool_to_call: str = Field(..., description="Name of the tool to run. Must be one of: 'lead_analytics', 'sales_analytics', 'search_prds', 'search_conversations', 'pricing_lookup', 'automation_status', 'system_health', 'knowledge_lookup', or 'none'.")
    search_query: str = Field("", description="The query parameter or term to pass if searching for PRDs, conversations, or knowledge.")


# ── CONTROLLED DISPATCHER TOOLS ────────────────────────────────────────────────

def get_lead_analytics():
    """Get lead discovery and qualification counts (§77)."""
    total = Lead.query.count()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_leads = Lead.query.filter(Lead.created_at >= today_start).count()
    
    categories_raw = db.session.query(Lead.business_category, db.func.count(Lead.id)).group_by(Lead.business_category).all()
    categories = {cat or 'unknown': count for cat, count in categories_raw}
    
    statuses_raw = db.session.query(Lead.status, db.func.count(Lead.id)).group_by(Lead.status).all()
    statuses = {status: count for status, count in statuses_raw}
    
    return {
        "total_leads": total,
        "leads_discovered_today": today_leads,
        "by_category": categories,
        "by_status": statuses
    }


def get_sales_analytics():
    """Get sales funnel analytics (§77)."""
    negotiation = Lead.query.filter_by(status=LeadStatus.NEGOTIATION).count()
    interested = Lead.query.filter_by(status=LeadStatus.INTERESTED).count()
    won = Lead.query.filter_by(status=LeadStatus.WON).count()
    contacted = Lead.query.filter_by(status=LeadStatus.CONTACTED).count()
    replied = Lead.query.filter_by(status=LeadStatus.REPLIED).count()
    
    return {
        "contacted": contacted,
        "replied": replied,
        "interested": interested,
        "negotiations": negotiation,
        "deals_won": won
    }


def search_prds(query_str):
    """Search generated PRD titles and statuses (§77)."""
    if not query_str:
        prds = PRD.query.order_by(PRD.updated_at.desc()).limit(5).all()
    else:
        prds = PRD.query.join(Lead).filter(
            (Lead.business_name.ilike(f"%{query_str}%")) |
            (PRD.title.ilike(f"%{query_str}%"))
        ).all()
        
    return [{
        "id": p.id,
        "title": p.title,
        "business": p.lead.business_name if p.lead else "Unknown",
        "status": p.status,
        "version": p.current_version
    } for p in prds]


def search_conversations(query_str):
    """Search chat threads and messages (§77)."""
    if not query_str:
        conversations = Conversation.query.order_by(Conversation.updated_at.desc()).limit(5).all()
    else:
        conversations = Conversation.query.join(Lead).filter(
            (Lead.business_name.ilike(f"%{query_str}%"))
        ).all()
        
    results = []
    for c in conversations:
        last_msg = c.messages.order_by(Message.created_at.desc()).first()
        results.append({
            "id": c.id,
            "business": c.lead.business_name if c.lead else "Unknown",
            "channel": c.channel,
            "status": c.status,
            "last_message": last_msg.content if last_msg else ""
        })
    return results


def lookup_pricing():
    """Lookup active pricing plans and tiers (§77)."""
    plans = PricingPlan.query.filter_by(is_enabled=True).order_by(PricingPlan.sort_order).all()
    return [{
        "plan_name": p.plan_name,
        "price": p.price,
        "currency": p.currency,
        "features": p.features,
        "maintenance_price": p.maintenance_price
    } for p in plans]


def get_automation_status():
    """Lookup scheduled background automation jobs (§77)."""
    jobs = AutomationJob.query.all()
    return [{
        "name": j.name,
        "job_type": j.job_type,
        "status": j.status,
        "schedule": j.schedule_cron,
        "last_run": j.last_run_at.isoformat() if j.last_run_at else "Never",
        "next_run": j.next_run_at.isoformat() if j.next_run_at else "Not scheduled"
    } for j in jobs]


def get_system_health():
    """Get model configuration status (§77)."""
    providers = LLMProvider.query.all()
    return [{
        "name": p.name,
        "protocol": p.protocol,
        "status": p.status,
        "priority": p.priority,
        "is_enabled": p.is_enabled,
        "failure_count": p.failure_count
    } for p in providers]


def lookup_knowledge(query_str=""):
    """Search agency knowledge base entries for company rules, PRD guides, and FAQs."""
    query = KnowledgeBase.query.filter_by(is_enabled=True)
    if query_str:
        query = query.filter(
            (KnowledgeBase.title.ilike(f"%{query_str}%")) |
            (KnowledgeBase.content.ilike(f"%{query_str}%")) |
            (KnowledgeBase.category.ilike(f"%{query_str}%"))
        )
    entries = query.limit(10).all()
    return [{
        "category": e.category,
        "title": e.title,
        "content": e.content
    } for e in entries]


# ── MAIN DISPATCHER ────────────────────────────────────────────────────────────

def answer_admin_query(query, history=None, image_path=None, model_name=None):
    """
    Classify query, dispatch tool retrieval, and generate final assistant answer with conversation memory.
    Supports multimodal image analysis if image_path is provided.
    Optimized for token efficiency and optional model override.
    """
    if not query and not image_path:
        return {"success": False, "error": "Query message or image must be provided."}

    user_query = query or "Please analyze this uploaded image and provide insights."
    logger.info(f"Admin Assistant processing query: '{user_query}' (model: {model_name}, image_path: {image_path})")

    # Token Optimization: Truncate history to last 6 messages and max 300 chars each
    history_text = ""
    if history:
        recent_history = history[-6:]
        lines = []
        for item in recent_history:
            role = "Admin" if item.get("sender") == "user" else "Assistant"
            content = (item.get("content") or "").strip()
            if len(content) > 300:
                content = content[:300] + "..."
            lines.append(f"{role}: {content}")
        history_text = "\n".join(lines)

    # Handle image attachment
    image_base64 = None
    image_mime = "image/jpeg"
    image_info_text = ""

    if image_path:
        full_path = image_path
        if not os.path.isabs(full_path):
            full_path = os.path.join(current_app.config.get('BASE_DIR', ''), full_path.lstrip('/\\'))
            
        if os.path.exists(full_path):
            try:
                mime, _ = mimetypes.guess_type(full_path)
                image_mime = mime or "image/jpeg"
                with open(full_path, "rb") as img_f:
                    image_base64 = base64.b64encode(img_f.read()).decode("utf-8")
                file_size_kb = os.path.getsize(full_path) / 1024
                image_info_text = f"\n[User attached an image: filename='{os.path.basename(full_path)}', size={file_size_kb:.1f}KB, type={image_mime}]"

                # Auto-update Settings if image is a Logo or Pricing card
                fname = os.path.basename(full_path).lower()
                q_lower = user_query.lower()
                if 'logo' in q_lower or 'logo' in fname:
                    from app.models import Setting
                    logo_url = f"/files/assistant/{os.path.basename(full_path)}"
                    stg = Setting.query.filter_by(category='company', key='company_logo').first()
                    if not stg:
                        stg = Setting(category='company', key='company_logo', value=logo_url)
                        db.session.add(stg)
                    else:
                        stg.value = logo_url
                    db.session.commit()
                    logger.info(f"Auto-updated company_logo to {logo_url}")

                if any(w in q_lower for w in ['price', 'prize', 'rate', 'cost', 'plan', 'package']) or any(w in fname for w in ['price', 'prize', 'rate']):
                    from app.models import KnowledgeBase
                    kb = KnowledgeBase.query.filter_by(category='pricing', title='Custom Pricing & Rate Card').first()
                    kb_entry = f"Admin pricing image asset: /files/assistant/{os.path.basename(full_path)}. Note: {user_query}"
                    if not kb:
                        kb = KnowledgeBase(category='pricing', title='Custom Pricing & Rate Card', content=kb_entry, is_enabled=True)
                        db.session.add(kb)
                    else:
                        kb.content = f"{kb.content}\n{kb_entry}"
                    db.session.commit()
                    logger.info("Auto-registered pricing image in KnowledgeBase")

            except Exception as e_img:
                logger.warning(f"Could not read image file {full_path}: {e_img}")

    # 1. Parse intent - Concise prompt to minimize token usage
    tool = 'none'
    search_term = ''

    if not image_base64:
        intent_prompt = f"""
        Analyze Admin query and pick ONE tool from:
        ['lead_analytics', 'sales_analytics', 'search_prds', 'search_conversations', 'pricing_lookup', 'automation_status', 'system_health', 'knowledge_lookup', 'none']
        Admin query: "{user_query}"
        """
        try:
            schema = AssistantIntentSchema.model_json_schema()
            intent = llm_router.generate_structured_output(intent_prompt, schema, task_type='intent_parsing')
            tool = intent.get('tool_to_call', 'none')
            search_term = intent.get('search_query', '')
            logger.info(f"Parsed tool to call: {tool} (search term: '{search_term}')")
        except Exception as e:
            logger.warning(f"Intent parsing fallback: {e}")
            tool = 'none'

    # 2. Execute target tool and extract context string
    context_data = None
    if tool == 'lead_analytics':
        context_data = get_lead_analytics()
    elif tool == 'sales_analytics':
        context_data = get_sales_analytics()
    elif tool == 'search_prds':
        context_data = search_prds(search_term)
    elif tool == 'search_conversations':
        context_data = search_conversations(search_term)
    elif tool == 'pricing_lookup':
        context_data = lookup_pricing()
    elif tool == 'automation_status':
        context_data = get_automation_status()
    elif tool == 'system_health':
        context_data = get_system_health()
    elif tool == 'knowledge_lookup':
        context_data = lookup_knowledge(search_term)

    # 3. Formulate final prompt combining context data & history memory
    final_prompt = f"""
    You are the Flixora AI Sales Assistant, an intelligent partner assisting the Admin in managing leads, analyzing websites, reviewing PRDs, checking sales pipelines, and inspecting visual assets.
    
    Conversation History:
    {history_text}
    
    Admin Query:
    "{user_query}"
    {image_info_text}
    
    System Database Context (if any):
    {f"Tool '{tool}' returned: {str(context_data)}" if context_data is not None else "No tool context needed."}
    
    Instructions:
    - Provide a concise, highly structured, and directly helpful answer.
    - If an image is provided, provide an objective visual breakdown: note layout quality, branding, typography, call-to-action visibility, and practical design improvements.
    - If database records are returned in the context, format the numbers or lists nicely (use markdown bullet points, bold highlights).
    - If numbers or stats are missing or counts are 0, state it clearly without fabricating information.
    - Maintain a friendly, sharp, and professional tone.
    """

    task_type = 'image_analysis' if image_base64 else 'assistant_response'
    options = {}
    if image_base64:
        options['image_base64'] = image_base64
        options['image_mime'] = image_mime
    if model_name:
        options['model'] = model_name

    try:
        reply = llm_router.generate_text(final_prompt, task_type=task_type, options=options)
        return {
            "success": True,
            "tool_called": tool,
            "reply": reply
        }
    except Exception as e:
        logger.error(f"Error executing Admin Assistant query: {e}")
        # Deterministic contextual answer fallback if external LLM fails
        if context_data:
            reply_fallback = f"Here are the database results for your query:\n\n```json\n{str(context_data)}\n```"
        elif image_base64:
            fname = os.path.basename(image_path).lower()
            q_lower = user_query.lower()
            if 'logo' in q_lower or 'logo' in fname:
                reply_fallback = (
                    "✅ **Company Logo Successfully Registered & Updated!**\n\n"
                    f"- **Asset**: `{os.path.basename(image_path)}`\n"
                    f"- **Saved Path**: `/files/assistant/{os.path.basename(image_path)}`\n"
                    "- **Status**: Registered as the official company brand logo in Company Settings.\n"
                    "- All future prototype preview headers and outreach assets will feature this branding."
                )
            elif any(w in q_lower for w in ['price', 'prize', 'rate', 'cost', 'plan', 'package']) or any(w in fname for w in ['price', 'prize', 'rate']):
                reply_fallback = (
                    "✅ **Pricing Details Registered & Updated!**\n\n"
                    f"- **Asset**: `{os.path.basename(image_path)}`\n"
                    "- **Status**: Saved to agency Knowledge Base under category **Pricing**.\n"
                    "- The Flixora AI WhatsApp agent is now armed with this pricing reference to answer client cost inquiries."
                )
            else:
                reply_fallback = (
                    "**Image Received & Registered.**\n\n"
                    f"- Image File: `{os.path.basename(image_path)}`\n"
                    f"- MIME Type: `{image_mime}`\n"
                    "- Status: Uploaded and saved to session media records."
                )
        else:
            reply_fallback = f"I received your request: '{user_query}'. However, the external AI model is currently unreachable ({str(e)}). Please check Settings -> LLM Providers."

        return {
            "success": True,
            "tool_called": tool,
            "reply": reply_fallback
        }
