"""
Flixora AI Sales Automation Agent — Admin AI Assistant Service
"""
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from flask import current_app

from app.extensions import db
from app.models import (
    Lead, PRD, Conversation, Message, PricingPlan,
    AutomationJob, LLMProvider, User
)
from app.constants import PRDStatus, LeadStatus, ProviderStatus
from app.ai.llm_router import llm_router
from app.utils.logger import get_logger

logger = get_logger('services')


class AssistantIntentSchema(BaseModel):
    """Pydantic schema for parsing user intent/tool selection."""
    tool_to_call: str = Field(..., description="Name of the tool to run. Must be one of: 'lead_analytics', 'sales_analytics', 'search_prds', 'search_conversations', 'pricing_lookup', 'automation_status', 'system_health', or 'none'.")
    search_query: str = Field("", description="The query parameter or term to pass if searching for PRDs or conversations.")


# ── CONTROLLED DISPATCHER TOOLS ────────────────────────────────────────────────

def get_lead_analytics():
    """Get lead discovery and qualification counts (§77)."""
    total = Lead.query.count()
    
    # Today's leads
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_leads = Lead.query.filter(Lead.created_at >= today_start).count()
    
    # Category counts
    categories_raw = db.session.query(Lead.business_category, db.func.count(Lead.id)).group_by(Lead.business_category).all()
    categories = {cat or 'unknown': count for cat, count in categories_raw}
    
    # Status counts
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
    # Count leads in negotiation, interested, won
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
        # Return pending/recent PRDs if query is empty
        prds = PRD.query.order_by(PRD.updated_at.desc()).limit(5).all()
    else:
        prds = PRD.query.join(Lead).filter(
            (Lead.business_name.ilike(f"%{query_str}%")) |
            (PRD.title.ilike(f"%{query_str}%"))
        ).all()
        
    return [{
        "id": p.id,
        "title": p.title,
        "business": p.lead.business_name,
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
        last_msg = Message.query.filter_by(conversation_id=c.id).order_by(Message.created_at.desc()).first()
        results.append({
            "id": c.id,
            "business": c.lead.business_name,
            "status": c.status,
            "last_message": last_msg.content if last_msg else 'No messages yet.'
        })
    return results


def lookup_pricing():
    """Get active plans list (§77)."""
    plans = PricingPlan.query.filter_by(is_active=True).all()
    return [{
        "name": p.name,
        "code": p.code,
        "price": p.price_amount,
        "currency": p.price_currency,
        "billing": p.billing_cycle
    } for p in plans]


def get_automation_status():
    """Get scheduler jobs details (§77)."""
    jobs = AutomationJob.query.all()
    return [{
        "name": j.name,
        "task_name": j.task_name,
        "interval_seconds": j.interval_seconds,
        "is_enabled": j.is_enabled,
        "last_run": j.last_run_at.isoformat() if j.last_run_at else None,
        "next_run": j.next_run_at.isoformat() if j.next_run_at else None
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


# ── MAIN DISPATCHER ────────────────────────────────────────────────────────────

def answer_admin_query(query, history=None):
    """
    Classify query, dispatch tool retrieval, and generate final assistant answer with conversation memory.
    """
    if not query:
        return {"success": False, "error": "Query cannot be empty."}

    logger.info(f"Admin Assistant processing query: '{query}'")

    # Format history context if provided
    history_text = ""
    if history:
        for item in history:
            role = "Admin" if item.get("sender") == "user" else "Assistant"
            history_text += f"{role}: {item.get('content')}\n"

    # 1. Parse intent using Pydantic JSON schema mode
    intent_prompt = f"""
    You are an intent classification engine for the Flixora Sales Dashboard.
    Analyze the Admin user query in context of the conversation history.
    
    Conversation History:
    {history_text}
    
    Admin user query:
    "{query}"
    
    Classify which controlled database tool should be executed to answer this query.
    Choose exactly one tool_to_call from this list:
    - 'lead_analytics': For questions about leads counts, leads found, category/status statistics, leads found today, rating criteria.
    - 'sales_analytics': For questions about deals won, pipeline conversions, closed sales, negotiations count, replies or contacted clients.
    - 'search_prds': For questions asking to show/list PRDs, look up PRD specifications or sitemaps.
    - 'search_conversations': For questions about client chats, messages received, chat threads.
    - 'pricing_lookup': For questions looking up plans, standard costs, billing details.
    - 'automation_status': For questions checking cron jobs, discovering scheduler tasks or automation metrics.
    - 'system_health': For questions checking LLM providers, API keys validity, or latency warnings.
    - 'none': If it is a generic question or chat greeting.
    
    If the query has a search term (like a business name), extract it into search_query.
    """

    try:
        schema = AssistantIntentSchema.model_json_schema()
        intent = llm_router.generate_structured_output(intent_prompt, schema, task_type='intent_parsing')
        
        tool = intent.get('tool_to_call', 'none')
        search_term = intent.get('search_query', '')
        
        logger.info(f"Parsed tool to call: {tool} (search term: '{search_term}')")
        
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

        # 3. Formulate final prompt combining context data & history memory
        final_prompt = f"""
        You are the Flixora AI Sales Assistant, a professional helper answering dashboard metrics for the Admin.
        
        Conversation History:
        {history_text}
        
        Admin Query:
        "{query}"
        
        System Database Context (if any):
        {f"Tool '{tool}' returned: {str(context_data)}" if context_data is not None else "No tool context needed."}
        
        Instructions:
        - Provide a concise, clear and directly helpful answer.
        - If database records are returned in the context, format the numbers or lists nicely (e.g. use markdown bullet points for lists).
        - If numbers or stats are missing or counts are 0, state it clearly without fabricating information.
        - Maintain a friendly and professional tone.
        """

        reply = llm_router.generate_text(final_prompt, task_type='assistant_response')
        return {
            "success": True,
            "tool_called": tool,
            "reply": reply
        }

    except Exception as e:
        logger.error(f"Error executing Admin Assistant query: {e}")
        return {
            "success": False,
            "error": f"Assistant query failed: {str(e)}"
        }
