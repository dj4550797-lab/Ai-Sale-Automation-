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
            try:
                db.session.rollback()
            except Exception:
                pass
            app.logger.error(f"Health check failed: {str(e)}")
            return {"status": "unhealthy", "database": "error", "error": str(e)}, 500

    # Favicon endpoints to eliminate 404 console errors
    @app.route('/favicon.ico')
    @app.route('/favicon.svg')
    def favicon():
        """Serve application favicon directly to eliminate 404 errors."""
        from flask import send_from_directory
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.svg', mimetype='image/svg+xml')

    # Auto-run lightweight startup migrations and seeding
    _run_startup_migrations(app)

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
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
            return None


def _run_startup_migrations(flask_app):
    """Run lightweight schema updates and ensure missing tables/columns exist."""
    from app.utils.logger import get_logger
    logger = get_logger('system')
    with flask_app.app_context():
        from app.extensions import db
        import app.models  # noqa
        from sqlalchemy import text

        try:
            db.create_all()
        except Exception as e:
            logger.warning(f"Startup create_all notice: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass

        # Safe ALTER statements for newly added columns across tables
        try:
            db.session.execute(text("SET statement_timeout = '3000'"))
        except Exception:
            pass
        migration_statements = [
            "ALTER TABLE outreach_campaigns ADD COLUMN media_url VARCHAR(500) DEFAULT NULL",
            "ALTER TABLE outreach_campaigns ADD COLUMN media_type VARCHAR(20) DEFAULT NULL",
            "ALTER TABLE leads ADD COLUMN business_hours VARCHAR(500) DEFAULT ''",
            "ALTER TABLE leads ADD COLUMN google_place_id VARCHAR(300)",
            "ALTER TABLE messages ADD COLUMN detected_intent VARCHAR(100) DEFAULT ''",
            "ALTER TABLE messages ADD COLUMN confidence FLOAT DEFAULT 0.0",
            "ALTER TABLE messages ADD COLUMN sales_stage VARCHAR(50) DEFAULT ''",
            "ALTER TABLE automation_runs DROP CONSTRAINT IF EXISTS automation_runs_lock_key_key",
        ]
        for stmt in migration_statements:
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass

        # Ensure admin user exists
        try:
            from app.services.auth_service import create_admin_user
            create_admin_user(
                username=flask_app.config.get('ADMIN_USERNAME', 'admin'),
                email=flask_app.config.get('ADMIN_EMAIL', 'admin@flixora.com'),
                password=flask_app.config.get('ADMIN_PASSWORD', 'admin123'),
                display_name='Admin',
            )
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        # Ensure default settings, LLMs, knowledge base, and pricing plans exist
        try:
            _seed_defaults(db)
        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            logger.warning(f"Startup defaults seed notice: {e}")

        # Ensure flyer pricing is in KnowledgeBase and ensure user requested lead exists
        try:
            from app.models import KnowledgeBase, Lead, LeadContact, PRD, DemoProject
            # 1. Update/Add Flyer Pricing to KnowledgeBase
            flyer_kb = KnowledgeBase.query.filter_by(category='pricing', title='Flixora Web Solutions — Official Pricing & Packages').first()
            flyer_content = (
                "Official Flixora Web Solutions Rates & Packages:\n"
                "• Basic Website Package: ₹2,999 — 1-Page responsive landing page with WhatsApp CTAs and Google Maps.\n"
                "• Standard Website Package: ₹5,999 — Complete multi-section business website with gallery, booking flow, and local SEO.\n"
                "• Premium Website Package: ₹9,999 — Custom animated corporate showcase, high conversions, and CRM integration.\n"
                "• E-Commerce Store Package: ₹14,999+ — Full store with product catalog, cart, online payment gateway (UPI/Razorpay/Stripe), and order tracking.\n"
                "• Animated Website Package: Custom dynamic 3D/micro-animations on demand.\n"
                "• Annual Care & Domain Renewal: ₹4,999/year — Cloud hosting, SSL security, and ongoing updates.\n"
                "• Official Support & Sales Contact: +91 8793393102 (Flixora Web Solutions)."
            )
            if not flyer_kb:
                flyer_kb = KnowledgeBase(category='pricing', title='Flixora Web Solutions — Official Pricing & Packages', content=flyer_content, is_enabled=True)
                db.session.add(flyer_kb)
            else:
                flyer_kb.content = flyer_content
                flyer_kb.is_enabled = True

            # 2. Delete Lead 36 if it exists
            lead_36 = Lead.query.get(36)
            if lead_36:
                db.session.delete(lead_36)

            # 3. Create/Ensure Lead with +91 7292894723
            target_phone = "917292894723"
            target_contact = LeadContact.query.filter(
                (LeadContact.value.ilike(f"%{target_phone}%")) |
                (LeadContact.value.ilike("%7292894723%"))
            ).first()
            if not target_contact:
                new_lead = Lead(
                    business_name="Flixora Premium Partner Client",
                    business_category="Web & E-Commerce Services",
                    status='qualified',
                    source_type='manual_admin',
                    city='Mumbai',
                    country='India'
                )
                db.session.add(new_lead)
                db.session.flush()

                c_item = LeadContact(
                    lead_id=new_lead.id,
                    contact_type='phone',
                    value="+91 7292894723",
                    is_primary=True
                )
                db.session.add(c_item)

                prd_item = PRD(
                    lead_id=new_lead.id,
                    title="Website Prototype for Flixora Client (+91 7292894723)",
                    status='approved',
                    website_goal="Showcase premium modern design, increase inbound WhatsApp sales, and demonstrate dynamic pricing flow.",
                    design_direction="Modern dark gradient with mobile-first WhatsApp quick-contact CTAs"
                )
                db.session.add(prd_item)
                db.session.flush()

                demo_item = DemoProject(
                    lead_id=new_lead.id,
                    prd_id=prd_item.id,
                    title="Flixora Web Solutions Interactive Prototype",
                    demo_url=f"/demos/preview/{new_lead.id}",
                    status='ready'
                )
                db.session.add(demo_item)

            db.session.commit()
            logger.info("Startup migration: Flyer pricing and +91 7292894723 lead verified.")
        except Exception as e_seed:
            try:
                db.session.rollback()
            except Exception:
                pass
            logger.warning(f"Notice during flyer/lead sync: {e_seed}")


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

        try:
            db.session.execute(text("ALTER TABLE leads ADD COLUMN business_hours VARCHAR(500) DEFAULT ''"))
            db.session.commit()
            click.echo("Migrated: Added 'business_hours' to 'leads' table.")
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(text("ALTER TABLE leads ADD COLUMN google_place_id VARCHAR(300)"))
            db.session.commit()
            click.echo("Migrated: Added 'google_place_id' to 'leads' table.")
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(text("ALTER TABLE outreach_campaigns ADD COLUMN media_url VARCHAR(500) DEFAULT NULL"))
            db.session.commit()
            click.echo("Migrated: Added 'media_url' to 'outreach_campaigns' table.")
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(text("ALTER TABLE outreach_campaigns ADD COLUMN media_type VARCHAR(20) DEFAULT NULL"))
            db.session.commit()
            click.echo("Migrated: Added 'media_type' to 'outreach_campaigns' table.")
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(text("UPDATE automation_runs SET lock_key = 'run_' || id WHERE lock_key = '' OR lock_key IS NULL"))
            db.session.execute(text("UPDATE automation_runs SET status = 'failed' WHERE status = 'running'"))
            db.session.commit()
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

        # Seed credential (use environment variable if available, else placeholder)
        initial_openrouter_key = os.environ.get('OPENROUTER_API_KEY', '').strip() or "sk-or-v1-dummy-openrouter-key-replace-me"
        cred = APICredential(
            provider_id=openrouter.id,
            credential_type='api_key',
            service_name='openrouter primary',
            encrypted_value=encrypt_value(initial_openrouter_key),
            last_four=initial_openrouter_key[-4:]
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
            initial_gemini_key = os.environ.get('GOOGLE_AI_API_KEY', '').strip() if i == 1 else ''
            gemini_key_val = initial_gemini_key or f"dummy-google-ai-studio-key-{i}-replace-me"
            gprov = LLMProvider(
                name=gname,
                protocol=LLMProtocol.GEMINI,
                status=ProviderStatus.HEALTHY if initial_gemini_key else ProviderStatus.DISABLED,
                priority=i + 1,  # priority 2, 3, 4
                is_enabled=True
            )
            db.session.add(gprov)
            db.session.commit()

            gcred = APICredential(
                provider_id=gprov.id,
                credential_type='api_key',
                service_name=gname.lower(),
                encrypted_value=encrypt_value(gemini_key_val),
                last_four=gemini_key_val[-4:]
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

    # 5. Seed Knowledge Base and Pricing Plans
    try:
        from app.seeds.seed_data import seed_knowledge_and_pricing
        seed_knowledge_and_pricing(db)
    except Exception as e:
        from app.utils.logger import get_logger
        get_logger('system').warning(f"Could not seed knowledge base / pricing: {e}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        from app.utils.logger import get_logger
        get_logger('system').warning(f"Could not commit seeded defaults: {e}")


def _register_error_handlers(app):
    """Register error page handlers."""
    from flask import render_template
    from app.extensions import db

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"Internal 500 error encountered: {e}", exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        try:
            db.session.remove()
        except Exception:
            pass


def _register_context(app):
    """Register template context processors."""
    from app.models import Notification, Setting
    from flask_login import current_user
    from app.extensions import db

    @app.context_processor
    def inject_globals():
        unread_notifications = 0
        company_name = 'Flixora'
        company_logo = '/static/img/logo.svg'
        try:
            if current_user and current_user.is_authenticated:
                unread_notifications = Notification.query.filter_by(
                    user_id=current_user.id, is_read=False
                ).count()
            
            c_name_stg = Setting.query.filter_by(category='company', key='company_name').first()
            if c_name_stg and c_name_stg.value:
                company_name = c_name_stg.value

            c_logo_stg = Setting.query.filter_by(category='company', key='company_logo').first()
            if c_logo_stg and c_logo_stg.value:
                company_logo = c_logo_stg.value
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        return {
            'app_name': company_name or 'Flixora',
            'company_name': company_name or 'Flixora',
            'company_logo': company_logo,
            'unread_notifications': unread_notifications,
        }
