"""
Flixora AI Sales Automation Agent — Model Registry

All models are imported here so SQLAlchemy discovers them.
"""
from app.models.user import User
from app.models.setting import Setting
from app.models.lead import Lead
from app.models.contact import LeadContact
from app.models.social_profile import SocialProfile
from app.models.lead_source import LeadSource
from app.models.website_analysis import WebsiteAnalysis
from app.models.lead_qualification import LeadQualification
from app.models.prd import PRD
from app.models.prd_version import PRDVersion
from app.models.demo import DemoProject
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.outreach import OutreachCampaign, OutreachEvent
from app.models.followup import FollowUp
from app.models.pricing import PricingPlan, DiscountRule
from app.models.sale import SalesDeal, SalesEvent
from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel
from app.models.api_credential import APICredential
from app.models.automation_job import AutomationJob
from app.models.automation_run import AutomationRun
from app.models.performance_event import PerformanceEvent
from app.models.correction_rule import CorrectionRule
from app.models.knowledge_base import KnowledgeBase
from app.models.uploaded_file import UploadedFile
from app.models.notification import Notification
from app.models.activity_log import ActivityLog

__all__ = [
    'User', 'Setting',
    'Lead', 'LeadContact', 'SocialProfile', 'LeadSource',
    'WebsiteAnalysis', 'LeadQualification',
    'PRD', 'PRDVersion',
    'DemoProject',
    'Conversation', 'Message',
    'OutreachCampaign', 'OutreachEvent',
    'FollowUp',
    'PricingPlan', 'DiscountRule',
    'SalesDeal', 'SalesEvent',
    'LLMProvider', 'LLMModel', 'APICredential',
    'AutomationJob', 'AutomationRun',
    'PerformanceEvent', 'CorrectionRule',
    'KnowledgeBase', 'UploadedFile',
    'Notification', 'ActivityLog',
]
