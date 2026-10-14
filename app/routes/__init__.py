"""
Flixora AI Sales Automation Agent — Route Registration

All blueprints are registered here.
"""
from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.settings import settings_bp
from app.routes.analytics import analytics_bp
from app.routes.automation import automation_bp
from app.routes.performance import performance_bp
from app.routes.logs import logs_bp
from app.routes.stubs import notifications_bp
from app.routes.providers import providers_bp
from app.routes.models import models_bp
from app.routes.credentials_api import credentials_api_bp
from app.routes.leads import leads_bp
from app.routes.analysis import analysis_bp
from app.routes.prds import prds_bp
from app.routes.knowledge import knowledge_bp
from app.routes.ai_assistant import ai_assistant_bp
from app.routes.files import files_bp
from app.routes.demos import demos_bp
from app.routes.outreach import outreach_bp
from app.routes.followups import followups_bp
from app.routes.sales import sales_bp
from app.routes.conversations import conversations_bp


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    # Core routes
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(credentials_api_bp)

    # Stub routes (to be replaced in later phases)
    app.register_blueprint(leads_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(prds_bp)
    app.register_blueprint(demos_bp)
    app.register_blueprint(outreach_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(followups_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(ai_assistant_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(providers_bp)
    app.register_blueprint(automation_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(logs_bp)
