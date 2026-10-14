"""
Flixora AI Sales Automation Agent — Application Constants

All enumerations and constant values used across the application.
"""


# ── Lead Statuses ──────────────────────────────────────────────
class LeadStatus:
    NEW = 'new'
    RESEARCHING = 'researching'
    RESEARCHED = 'researched'
    QUALIFIED = 'qualified'
    DISQUALIFIED = 'disqualified'
    CONTACTED = 'contacted'
    REPLIED = 'replied'
    INTERESTED = 'interested'
    NEGOTIATION = 'negotiation'
    WON = 'won'
    LOST = 'lost'
    PAUSED = 'paused'
    WAITING_FOR_DEMO = 'Waiting for Admin Demo'

    ALL = [NEW, RESEARCHING, RESEARCHED, QUALIFIED, DISQUALIFIED,
           CONTACTED, REPLIED, INTERESTED, NEGOTIATION, WON, LOST, PAUSED, WAITING_FOR_DEMO]


# ── Lead Priority ──────────────────────────────────────────────
class LeadPriority:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

    ALL = [LOW, MEDIUM, HIGH, CRITICAL]


# ── PRD Statuses ───────────────────────────────────────────────
class PRDStatus:
    DRAFT = 'draft'
    READY = 'ready'
    UNDER_REVIEW = 'under_review'
    CHANGES_REQUESTED = 'changes_requested'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    ALL = [DRAFT, READY, UNDER_REVIEW, CHANGES_REQUESTED, APPROVED, REJECTED]


# ── Outreach Statuses ─────────────────────────────────────────
class OutreachStatus:
    READY = 'ready'
    APPROVAL_REQUIRED = 'approval_required'
    SCHEDULED = 'scheduled'
    SENT = 'sent'
    DELIVERED = 'delivered'
    REPLIED = 'replied'
    FAILED = 'failed'
    STOPPED = 'stopped'
    PAUSED = 'paused'

    ALL = [READY, APPROVAL_REQUIRED, SCHEDULED, SENT, DELIVERED, REPLIED, FAILED, STOPPED, PAUSED]


# ── Conversation Statuses ─────────────────────────────────────
class ConversationStatus:
    AI_ACTIVE = 'ai_active'
    ADMIN_ACTIVE = 'admin_active'
    PAUSED = 'paused'
    CLOSED = 'closed'

    ALL = [AI_ACTIVE, ADMIN_ACTIVE, PAUSED, CLOSED]


# ── Sales Pipeline Stages ─────────────────────────────────────
class PipelineStage:
    NEW = 'new'
    CONTACTED = 'contacted'
    REPLIED = 'replied'
    INTERESTED = 'interested'
    NEGOTIATION = 'negotiation'
    WON = 'won'
    LOST = 'lost'

    ALL = [NEW, CONTACTED, REPLIED, INTERESTED, NEGOTIATION, WON, LOST]


# ── Follow-Up Statuses ────────────────────────────────────────
class FollowUpStatus:
    SCHEDULED = 'scheduled'
    SENT = 'sent'
    REPLIED = 'replied'
    STOPPED = 'stopped'
    CANCELLED = 'cancelled'

    ALL = [SCHEDULED, SENT, REPLIED, STOPPED, CANCELLED]


# ── Notification Types ─────────────────────────────────────────
class NotificationType:
    PRD_READY = 'prd_ready'
    CLIENT_REPLY = 'client_reply'
    INTERESTED = 'interested'
    AUTOMATION_FAILURE = 'automation_failure'
    LLM_FAILURE = 'llm_failure'
    SECURITY_ALERT = 'security_alert'
    AGENT_ERROR = 'agent_error'
    DEAL_WON = 'deal_won'
    LEAD_QUALIFIED = 'lead_qualified'
    APPROVAL_REQUIRED = 'approval_required'

    ALL = [PRD_READY, CLIENT_REPLY, INTERESTED, AUTOMATION_FAILURE,
           LLM_FAILURE, SECURITY_ALERT, AGENT_ERROR, DEAL_WON,
           LEAD_QUALIFIED, APPROVAL_REQUIRED]


# ── AI Risk Levels ─────────────────────────────────────────────
class RiskLevel:
    LOW = 'low'
    CONTROLLED = 'controlled'
    HIGH = 'high'

    ALL = [LOW, CONTROLLED, HIGH]


# ── Provider Statuses ──────────────────────────────────────────
class ProviderStatus:
    HEALTHY = 'healthy'
    WARNING = 'warning'
    RATE_LIMITED = 'rate_limited'
    UNAVAILABLE = 'unavailable'
    DISABLED = 'disabled'

    ALL = [HEALTHY, WARNING, RATE_LIMITED, UNAVAILABLE, DISABLED]


# ── LLM Protocols ─────────────────────────────────────────────
class LLMProtocol:
    OPENAI_COMPATIBLE = 'openai_compatible'
    GEMINI = 'gemini'
    ANTHROPIC_COMPATIBLE = 'anthropic_compatible'
    CUSTOM_REST = 'custom_rest'

    ALL = [OPENAI_COMPATIBLE, GEMINI, ANTHROPIC_COMPATIBLE, CUSTOM_REST]


# ── Model Capabilities ────────────────────────────────────────
class ModelCapability:
    TEXT = 'text'
    VISION = 'vision'
    TOOL_CALLING = 'tool_calling'
    STRUCTURED_OUTPUT = 'structured_output'

    ALL = [TEXT, VISION, TOOL_CALLING, STRUCTURED_OUTPUT]


# ── Automation Job Statuses ────────────────────────────────────
class AutomationJobStatus:
    ACTIVE = 'active'
    PAUSED = 'paused'
    DISABLED = 'disabled'
    RUNNING = 'running'
    FAILED = 'failed'

    ALL = [ACTIVE, PAUSED, DISABLED, RUNNING, FAILED]


# ── Messaging Channels ────────────────────────────────────────
class MessagingChannel:
    WHATSAPP = 'whatsapp'
    INSTAGRAM = 'instagram'
    EMAIL = 'email'

    ALL = [WHATSAPP, INSTAGRAM, EMAIL]


# ── Activity Log Actions ──────────────────────────────────────
class ActivityAction:
    LOGIN = 'login'
    LOGOUT = 'logout'
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    APPROVE = 'approve'
    REJECT = 'reject'
    SEND = 'send'
    IMPORT = 'import'
    EXPORT = 'export'
    TAKEOVER = 'takeover'
    EMERGENCY_STOP = 'emergency_stop'

    ALL = [LOGIN, LOGOUT, CREATE, UPDATE, DELETE, APPROVE, REJECT,
           SEND, IMPORT, EXPORT, TAKEOVER, EMERGENCY_STOP]


# ── Duplicate Detection Results ────────────────────────────────
class DuplicateResult:
    UNIQUE = 'unique'
    LIKELY_DUPLICATE = 'likely_duplicate'
    CONFIRMED_DUPLICATE = 'confirmed_duplicate'

    ALL = [UNIQUE, LIKELY_DUPLICATE, CONFIRMED_DUPLICATE]


# ── Website Analysis Verdict ───────────────────────────────────
class WebsiteVerdict:
    NO_WEBSITE = 'no_website'
    NEEDS_IMPROVEMENT = 'needs_improvement'
    ADEQUATE = 'adequate'

    ALL = [NO_WEBSITE, NEEDS_IMPROVEMENT, ADEQUATE]


# ── Knowledge Base Categories ──────────────────────────────────
class KBCategory:
    COMPANY = 'company'
    SERVICES = 'services'
    PRICING = 'pricing'
    FAQS = 'faqs'
    SALES_RULES = 'sales_rules'
    POLICIES = 'policies'
    AGENT_RULES = 'agent_rules'

    ALL = [COMPANY, SERVICES, PRICING, FAQS, SALES_RULES, POLICIES, AGENT_RULES]


# ── Settings Categories ───────────────────────────────────────
class SettingsCategory:
    PROFILE = 'profile'
    COMPANY = 'company'
    AGENT = 'agent'
    PRICING = 'pricing'
    LLM = 'llm'
    INTEGRATIONS = 'integrations'
    AUTOMATION = 'automation'
    LEAD_DISCOVERY = 'lead_discovery'
    MESSAGING = 'messaging'
    SECURITY = 'security'
    NOTIFICATIONS = 'notifications'

    ALL = [PROFILE, COMPANY, AGENT, PRICING, LLM, INTEGRATIONS,
           AUTOMATION, LEAD_DISCOVERY, MESSAGING, SECURITY, NOTIFICATIONS]
