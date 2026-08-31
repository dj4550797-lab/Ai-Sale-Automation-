"""
Flixora AI Sales Automation Agent — Application Factory

Creates and configures the Flask application.
"""
import os
import click
from flask import Flask, redirect, url_for

from config import config


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))

    # Ensure required directories exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'images'), exist_ok=True)
    os.makedirs(os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'logos'), exist_ok=True)
    os.makedirs(os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'documents'), exist_ok=True)
    os.makedirs('instance', exist_ok=True)

    # Initialize extensions
    _init_extensions(app)

    # Register blueprints
    _register_blueprints(app)

    # Setup logging
    _setup_logging(app)

    # Register CLI commands
    _register_commands(app)

    # Register error handlers
    _register_error_handlers(app)

    # Register template context
    _register_context(app)

    # Root redirect
    @app.route('/')
    def root():
        return redirect(url_for('dashboard.index'))

    # Health check endpoint
    @app.route('/health')
    def health():
        """Health check endpoint checking database connectivity."""
        from app.extensions import db
        from sqlalchemy import text
        try:
            db.session.execute(text('SELECT 1'))
            return {"status": "healthy", "database": "connected"}, 200
        except Exception as e:
            app.logger.error(f"Health check failed: {str(e)}")
            return {"status": "unhealthy", "database": "error", "error": str(e)}, 500

    return app


def _init_extensions(app):
    """Initialize Flask extensions."""
    from app.extensions import db, login_manager, csrf, migrate
    from app.models.user import User

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


def _register_blueprints(app):
    """Register route blueprints."""
    from app.routes import register_blueprints
    register_blueprints(app)


def _setup_logging(app):
    """Configure application logging."""
    from app.utils.logger import setup_logging
    setup_logging(app)


def _register_commands(app):
    """Register Flask CLI commands."""
    from app.extensions import db
    from app.models import User, Setting, AutomationJob

    @app.cli.command('init-db')
    def init_db():
        """Create all database tables and seed default data."""
        # Import all models to ensure they're registered
        import app.models  # noqa

        db.create_all()
        click.echo('Database tables created.')

        # Schema migrations: Add missing message classification columns if they don't exist
        from sqlalchemy import text
        try:
            db.session.execute(text("ALTER TABLE messages ADD COLUMN detected_intent VARCHAR(100) DEFAULT ''"))
            db.session.commit()
            click.echo("Migrated: Added 'detected_intent' to 'messages' table.")
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(text("ALTER TABLE messages ADD COLUMN confidence FLOAT DEFAULT 0.0"))
            db.session.commit()
            click.echo("Migrated: Added 'confidence' to 'messages' table.")
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(text("ALTER TABLE messages ADD COLUMN sales_stage VARCHAR(50) DEFAULT ''"))
            db.session.commit()
            click.echo("Migrated: Added 'sales_stage' to 'messages' table.")
        except Exception:
            db.session.rollback()

        # Create default admin
        from flask import current_app
        from app.services.auth_service import create_admin_user
        admin = create_admin_user(
            username=current_app.config['ADMIN_USERNAME'],
            email=current_app.config['ADMIN_EMAIL'],
            password=current_app.config['ADMIN_PASSWORD'],
            display_name='Admin',
        )
        click.echo(f'Admin user: {admin.username}')

        # Seed default settings
        _seed_defaults(db)
        click.echo('Default settings created.')
        click.echo('Database initialized successfully!')

    @app.cli.command('generate-key')
    def generate_key():
        """Generate a new Fernet encryption key."""
        from app.security.encryption import generate_encryption_key
        key = generate_encryption_key()
        click.echo(f'New encryption key: {key}')
        click.echo('Add this to your .env file as ENCRYPTION_KEY')


def _seed_defaults(db):
    """Seed default settings and LLM configurations."""
    from app.models import Setting, LLMProvider, LLMModel, APICredential
    from app.constants import ProviderStatus, LLMProtocol
    from app.security.encryption import encrypt_value

    defaults = [
        ('company', 'company_name', 'Flixora'),
        ('company', 'company_description', 'AI-powered website solutions for local businesses'),
        ('agent', 'agent_name', 'Flixora AI'),
        ('agent', 'agent_role', 'Sales Assistant'),
        ('agent', 'communication_tone', 'Professional and friendly'),
        ('lead_discovery', 'daily_lead_target', '20'),
        ('lead_discovery', 'default_country', 'India'),
        ('automation', 'global_enabled', 'true'),
        ('messaging', 'followup_limit', '3'),
        ('messaging', 'followup_delay_hours', '24'),
    ]

    for category, key, value in defaults:
        existing = Setting.query.filter_by(category=category, key=key).first()
        if not existing:
            db.session.add(Setting(category=category, key=key, value=value))

    # 1. Seed OpenRouter Provider
    openrouter = LLMProvider.query.filter_by(name='OpenRouter Primary').first()
    if not openrouter:
        openrouter = LLMProvider(
            name='OpenRouter Primary',
            protocol=LLMProtocol.OPENAI_COMPATIBLE,
            base_url='https://openrouter.ai/api/v1',
            status=ProviderStatus.HEALTHY,
            priority=1,
            is_enabled=True
        )
        db.session.add(openrouter)
        db.session.commit()

        # Seed dummy credential (masking sk-or-v1-...)
        dummy_key = "sk-or-v1-dummy-openrouter-key-replace-me"
        cred = APICredential(
            provider_id=openrouter.id,
            credential_type='api_key',
            service_name='openrouter primary',
            encrypted_value=encrypt_value(dummy_key),
            last_four=dummy_key[-4:]
        )
        db.session.add(cred)

        # Seed models
        mini = LLMModel(
            provider_id=openrouter.id,
            model_id='openai/gpt-4o-mini',
            display_name='GPT-4o Mini',
            priority=1,
            supports_text=True,
            supports_structured_output=True,
            is_enabled=True
        )
        gemini_free = LLMModel(
            provider_id=openrouter.id,
            model_id='google/gemini-2.0-flash-exp:free',
            display_name='Gemini 2.0 Flash Exp (Free)',
            priority=2,
            supports_text=True,
            supports_structured_output=True,
            is_enabled=True
        )
        db.session.add_all([mini, gemini_free])

    # 2. Seed 3 Fallback Google AI Studio accounts
    for i in range(1, 4):
        gname = f'Google AI Studio fallback {i}'
        existing_g = LLMProvider.query.filter_by(name=gname).first()
        if not existing_g:
            gprov = LLMProvider(
                name=gname,
                protocol=LLMProtocol.GEMINI,
                status=ProviderStatus.DISABLED,
                priority=i + 1,  # priority 2, 3, 4
                is_enabled=True
            )
            db.session.add(gprov)
            db.session.commit()

            # Seed dummy key
            gkey = f"dummy-google-ai-studio-key-{i}-replace-me"
            gcred = APICredential(
                provider_id=gprov.id,
                credential_type='api_key',
                service_name=gname.lower(),
                encrypted_value=encrypt_value(gkey),
                last_four=gkey[-4:]
            )
            db.session.add(gcred)

            # Seed Gemini model
            gmodel = LLMModel(
                provider_id=gprov.id,
                model_id='gemini-2.5-flash',
                display_name='Gemini 2.5 Flash',
                priority=1,
                supports_text=True,
                supports_structured_output=True,
                is_enabled=True
            )
            db.session.add(gmodel)

    # 3. Seed xAI (Grok) Provider — OpenAI compatible
    xai_provider = LLMProvider.query.filter_by(name='xAI (Grok)').first()
    if not xai_provider:
        xai_provider = LLMProvider(
            name='xAI (Grok)',
            protocol=LLMProtocol.OPENAI_COMPATIBLE,
            base_url='https://api.x.ai/v1',
            status=ProviderStatus.DISABLED,
            priority=5,
            is_enabled=True
        )
        db.session.add(xai_provider)
        db.session.commit()

        xai_key = "xai-dummy-grok-api-key-replace-me"
        xai_cred = APICredential(
            provider_id=xai_provider.id,
            credential_type='api_key',
            service_name='xai (grok)',
            encrypted_value=encrypt_value(xai_key),
            last_four=xai_key[-4:]
        )
        db.session.add(xai_cred)

        # Grok models
        grok3 = LLMModel(
            provider_id=xai_provider.id,
            model_id='grok-3',
            display_name='Grok 3',
            priority=1,
            supports_text=True,
            supports_structured_output=True,
            supports_tool_calling=True,
            is_enabled=True
        )
        grok3_mini = LLMModel(
            provider_id=xai_provider.id,
            model_id='grok-3-mini',
            display_name='Grok 3 Mini',
            priority=2,
            supports_text=True,
            supports_structured_output=True,
            is_enabled=True
        )
        db.session.add_all([grok3, grok3_mini])

    # 4. Add extra models to OpenRouter (if exists)
    if openrouter:
        extra_models = [
            ('anthropic/claude-sonnet-4', 'Claude Sonnet 4', 3),
            ('x-ai/grok-3', 'Grok 3 (via OpenRouter)', 4),
            ('meta-llama/llama-4-maverick', 'Llama 4 Maverick', 5),
        ]
        for model_id, display_name, priority in extra_models:
            existing_m = LLMModel.query.filter_by(
                provider_id=openrouter.id, model_id=model_id
            ).first()
            if not existing_m:
                db.session.add(LLMModel(
                    provider_id=openrouter.id,
                    model_id=model_id,
                    display_name=display_name,
                    priority=priority,
                    supports_text=True,
                    supports_structured_output=True,
                    is_enabled=True
                ))

    # 5. Seed OpenCode Zen Provider — OpenAI compatible
    opencode_zen = LLMProvider.query.filter_by(name='OpenCode Zen').first()
    if not opencode_zen:
        opencode_zen = LLMProvider(
            name='OpenCode Zen',
            protocol=LLMProtocol.OPENAI_COMPATIBLE,
            base_url='https://opencode.ai/zen/v1',
            status=ProviderStatus.DISABLED,
            priority=6,
            is_enabled=True
        )
        db.session.add(opencode_zen)
        db.session.commit()

        opencode_key = "opencode-dummy-zen-key-replace-me"
        opencode_cred = APICredential(
            provider_id=opencode_zen.id,
            credential_type='api_key',
            service_name='opencode zen',
            encrypted_value=encrypt_value(opencode_key),
            last_four=opencode_key[-4:]
        )
        db.session.add(opencode_cred)

        # OpenCode Zen models
        model1 = LLMModel(
            provider_id=opencode_zen.id,
            model_id='opencode/kimi-k3',
            display_name='Kimi K3 (OpenCode)',
            priority=1,
            supports_text=True,
            supports_structured_output=True,
            is_enabled=True
        )
        model2 = LLMModel(
            provider_id=opencode_zen.id,
            model_id='opencode/gpt-5.6-sol',
            display_name='GPT-5.6 Sol (OpenCode)',
            priority=2,
            supports_text=True,
            supports_structured_output=True,
            is_enabled=True
        )
        db.session.add_all([model1, model2])

    db.session.commit()


def _register_error_handlers(app):
    """Register error page handlers."""
    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403


def _register_context(app):
    """Register template context processors."""
    from app.models import Notification
    from flask_login import current_user

    @app.context_processor
    def inject_globals():
        unread_notifications = 0
        if current_user and current_user.is_authenticated:
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()

        return {
            'app_name': 'Flixora',
            'unread_notifications': unread_notifications,
        }
