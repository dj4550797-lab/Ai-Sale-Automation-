# Flixora AI Sales Automation Agent — Implementation Plan

## Overview

Build the Flixora AI Sales Automation Agent: an AI-powered internal sales automation platform that automates lead discovery → qualification → PRD generation → outreach → client conversation → follow-up → deal closure for local-business website sales.

**Stack:** Python 3.12 + Flask + SQLAlchemy + SQLite | HTML5/CSS3/JS with Material Design 3 | White + Blue SaaS theme

**Environment:** Python 3.12.10 confirmed available. Empty workspace at `c:\Users\admin\Desktop\AI Sale Agent`.

---

## User Review Required

> [!IMPORTANT]
> **This is a very large project (~100+ files, ~28 modules).** The PRD specifies 8 development phases. I propose building Phase 1 first and getting your review before proceeding to subsequent phases. Each phase will be a self-contained, working increment.

> [!IMPORTANT]
> **Phase 1 scope decision:** Phase 1 (PRD §142) covers project setup, Flask, database, authentication, UI shell, theme, and settings. This alone is substantial (~40+ files). Should I proceed with Phase 1 in full, or would you prefer an even smaller first increment (e.g., just the project skeleton + auth + dashboard shell)?

> [!WARNING]
> **API Keys & Secrets:** The PRD mandates encrypted credential storage (§17-18). For Phase 1, I'll implement the encryption infrastructure with Fernet symmetric encryption. You'll need to set a `SECRET_KEY` and `ENCRYPTION_KEY` in `.env` before running.

---

## Open Questions

> [!IMPORTANT]
> **1. Virtual Environment:** Should I create a Python virtual environment (`venv`) in the project directory, or do you have a preferred environment management approach (conda, poetry, etc.)?

> [!IMPORTANT]
> **2. Material Design 3:** The PRD specifies MD3. Options:
> - **Option A (Recommended):** Use Google's Material Web Components (`@material/web`) via CDN — true MD3 with web components
> - **Option B:** Use a CSS-only MD3-inspired system hand-built for full control
> - **Option C:** Use a third-party MD3 CSS framework
>
> My recommendation is Option A for authenticity + Option B fallback where MD3 web components don't cover the need.

> [!IMPORTANT]
> **3. Database Migrations:** The PRD mentions migrations (§109). Should I set up Flask-Migrate (Alembic) from the start, or defer migrations to a later phase?

> [!IMPORTANT]  
> **4. Incremental Build Approach:** Given the 146-section PRD, I propose we build and review phase-by-phase. After each phase, you review and approve before I proceed. Does this approach work for you?

---

## Proposed Changes — Phase 1: Foundation

Phase 1 corresponds to PRD §142 Phase 1 and covers: project setup, Flask application factory, database models, authentication, UI shell with navigation, theme system, and settings infrastructure.

---

### Project Root & Configuration

#### [NEW] `requirements.txt`
Core dependencies: Flask, SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, Gunicorn, APScheduler, cryptography, Pydantic, requests, python-dotenv

#### [NEW] `.env.example`
Template with placeholder values for `SECRET_KEY`, `ENCRYPTION_KEY`, `DATABASE_URL`, `FLASK_ENV`, `FLASK_DEBUG`

#### [NEW] `.gitignore`
Python, Flask, venv, .env, instance/, uploads/, logs/, __pycache__, *.pyc

#### [NEW] `config.py`
Configuration classes (Development, Production, Testing) loading from environment variables. Database URI, session config, CSRF, upload paths.

#### [NEW] `app.py`
Application entry point. Creates Flask app via factory, runs dev server.

#### [NEW] `Procfile`
Gunicorn configuration for Render deployment.

#### [NEW] `README.md`
Project overview, setup instructions, development guide.

---

### Flask Application Factory

#### [NEW] `app/__init__.py`
Application factory (`create_app()`): registers extensions, blueprints, error handlers, template context processors, logging configuration.

#### [NEW] `app/extensions.py`
Extension instances: SQLAlchemy, LoginManager, CSRFProtect, Migrate, APScheduler.

#### [NEW] `app/constants.py`
Application-wide constants: status enums, lead statuses, PRD statuses, pipeline stages, notification types, risk levels.

#### [NEW] `app/decorators.py`
Custom decorators: `@admin_required`, `@api_response`, `@audit_log`.

---

### Database Models (§110-111)

All models use SQLAlchemy with separated fields per §21.

#### [NEW] `app/models/__init__.py` — Model registry
#### [NEW] `app/models/user.py` — Admin user (username, email, password_hash, timezone, profile_image)
#### [NEW] `app/models/setting.py` — Key-value settings with categories
#### [NEW] `app/models/lead.py` — Core lead (business_name, category, address, city, state, rating, review_count, status, lead_score, google_place_id)
#### [NEW] `app/models/contact.py` — Lead contacts (phone, whatsapp, email) — separate from lead
#### [NEW] `app/models/social_profile.py` — Social links (instagram_url, facebook_url, platform, profile_url)
#### [NEW] `app/models/lead_source.py` — Discovery source tracking
#### [NEW] `app/models/website_analysis.py` — Analysis results with separated criteria scores
#### [NEW] `app/models/lead_qualification.py` — Score, priority, reason, opportunity
#### [NEW] `app/models/prd.py` — PRD with status workflow (DRAFT→UNDER_REVIEW→APPROVED/REJECTED)
#### [NEW] `app/models/prd_version.py` — Version history with full PRD snapshot
#### [NEW] `app/models/demo.py` — Demo projects with explicit lead_id mapping
#### [NEW] `app/models/conversation.py` — Conversation sessions with status (AI_ACTIVE, ADMIN_ACTIVE, PAUSED, CLOSED)
#### [NEW] `app/models/message.py` — Individual messages with sender type
#### [NEW] `app/models/outreach.py` — Outreach campaigns and events
#### [NEW] `app/models/followup.py` — Follow-up scheduling and tracking
#### [NEW] `app/models/pricing.py` — Pricing plans (Basic, Standard, Advanced, etc.)
#### [NEW] `app/models/discount_rule.py` — Discount rules with min/max bounds
#### [NEW] `app/models/sale.py` — Sales deals and pipeline events
#### [NEW] `app/models/llm_provider.py` — LLM provider configuration
#### [NEW] `app/models/llm_model.py` — Model configuration per provider
#### [NEW] `app/models/api_credential.py` — Encrypted API credentials
#### [NEW] `app/models/automation_job.py` — Job definitions and run history
#### [NEW] `app/models/automation_run.py` — Individual run records
#### [NEW] `app/models/performance_event.py` — Performance tracking points
#### [NEW] `app/models/correction_rule.py` — Error correction rules
#### [NEW] `app/models/knowledge_base.py` — Knowledge base entries by category
#### [NEW] `app/models/uploaded_file.py` — File metadata and paths
#### [NEW] `app/models/notification.py` — Notification records
#### [NEW] `app/models/activity_log.py` — Audit trail records

---

### Security (§118-119)

#### [NEW] `app/security/__init__.py`
#### [NEW] `app/security/encryption.py` — Fernet-based credential encryption/decryption
#### [NEW] `app/security/permissions.py` — Permission checking utilities
#### [NEW] `app/security/csrf.py` — CSRF configuration
#### [NEW] `app/security/validation.py` — Input validation helpers
#### [NEW] `app/security/rate_limit.py` — Simple rate limiting (in-memory for Phase 1)

---

### Authentication Routes (§10)

#### [NEW] `app/routes/__init__.py` — Blueprint registration
#### [NEW] `app/routes/auth.py` — Login, logout, session management. Password hashing with werkzeug. CSRF protection. Rate limiting on login.

---

### Dashboard Route (§11-12)

#### [NEW] `app/routes/dashboard.py` — Dashboard page with KPI cards, funnel, recent activity, quick actions. Data sourced from services.

---

### Settings Routes (§91-97)

#### [NEW] `app/routes/settings.py` — Profile, company, agent, pricing, integrations, automation, security settings. API key input with masking (§60).

---

### UI Theme & Shell (§6-9)

#### [NEW] `app/templates/base.html`
Master template with:
- Left sidebar navigation (§8) with all nav items
- Top bar with page title, search, notifications, automation status, profile (§9)
- Content area
- Toast notification container
- Mobile drawer navigation
- MD3 component imports

#### [NEW] `app/templates/auth/login.html` — Login page (§10)
#### [NEW] `app/templates/dashboard/index.html` — Dashboard with KPI cards, funnel chart, activity feed, quick actions (§11-12)
#### [NEW] `app/templates/settings/index.html` — Settings page with tabbed sections
#### [NEW] `app/templates/settings/profile.html` — Profile settings
#### [NEW] `app/templates/settings/company.html` — Company settings
#### [NEW] `app/templates/settings/agent.html` — Agent configuration
#### [NEW] `app/templates/settings/integrations.html` — API key management with masked display

---

### CSS Design System (§6-7)

#### [NEW] `app/static/css/theme.css`
Design tokens: colors (white + blue palette), typography, spacing, shadows, border-radius. CSS custom properties for theming.

#### [NEW] `app/static/css/components.css`
Component styles: cards, tables, tabs, chips, badges, dropdowns, tooltips, dialogs, toasts, empty states, loading skeletons, progress indicators, buttons, forms, sidebar, topbar.

#### [NEW] `app/static/css/app.css`
Layout styles: sidebar layout, content area, page-specific layouts.

#### [NEW] `app/static/css/responsive.css`
Responsive breakpoints: desktop, laptop, tablet, mobile. Sidebar → drawer, tables → cards.

---

### JavaScript Foundation

#### [NEW] `app/static/js/app.js`
Core utilities: toast notifications, dialog management, CSRF token handling, fetch wrapper, sidebar toggle, search, theme initialization.

#### [NEW] `app/static/js/dashboard.js`
Dashboard-specific: KPI card updates, funnel visualization (CSS-based), activity feed.

#### [NEW] `app/static/js/settings.js`
Settings: tab switching, API key masking, form submission, test connection.

---

### Utilities

#### [NEW] `app/utils/__init__.py`
#### [NEW] `app/utils/logger.py` — Structured logging setup (app, ai, automation, security logs) with secret filtering (§88, §119)
#### [NEW] `app/utils/helpers.py` — Common helpers (date formatting, pagination, slug generation)
#### [NEW] `app/utils/time.py` — Timezone-aware time utilities

---

### Placeholder Stubs (for navigation to work)

#### [NEW] `app/routes/leads.py` — Stub with "Coming in Phase 3" empty state
#### [NEW] `app/routes/analysis.py` — Stub
#### [NEW] `app/routes/prds.py` — Stub
#### [NEW] `app/routes/demos.py` — Stub
#### [NEW] `app/routes/outreach.py` — Stub
#### [NEW] `app/routes/conversations.py` — Stub
#### [NEW] `app/routes/followups.py` — Stub
#### [NEW] `app/routes/sales.py` — Stub
#### [NEW] `app/routes/analytics.py` — Stub
#### [NEW] `app/routes/ai_assistant.py` — Stub
#### [NEW] `app/routes/knowledge.py` — Stub
#### [NEW] `app/routes/files.py` — Stub
#### [NEW] `app/routes/providers.py` — Stub
#### [NEW] `app/routes/automation.py` — Stub
#### [NEW] `app/routes/notifications.py` — Stub

#### [NEW] Corresponding stub templates for each route above

---

### Initial Data & Database Setup

#### [NEW] `app/services/__init__.py`
#### [NEW] `app/services/auth_service.py` — User creation, authentication, password management

The `create_app()` function will include a CLI command `flask init-db` to create tables and seed a default admin user.

---

## File Count Estimate

Phase 1 produces approximately **70-80 files** across models, routes, templates, static assets, security, and utilities.

---

## Verification Plan

### Automated Tests
- `python -m pytest tests/test_auth.py` — Login, logout, session, CSRF, rate limiting
- `python -m pytest tests/test_security.py` — Encryption, secret masking

### Manual Verification
- Start dev server with `python app.py`
- Login page renders with Flixora branding, white+blue theme
- Dashboard shows KPI cards (with zero data), funnel, empty activity feed, quick actions
- Sidebar navigation works, all stubs show appropriate empty states
- Settings page: profile, company, agent tabs work
- API key input masks properly
- Mobile responsive: sidebar becomes drawer
- CSRF protection active on all forms
- Password hashing verified

---

## Phases 2-8 Overview (for reference, built after Phase 1 approval)

| Phase | Scope | PRD Sections |
|-------|-------|-------------|
| **2** | LLM Provider Manager, Model Manager, Credential Manager, Fallback Router | §58-68, §100-101 |
| **3** | Lead Discovery, Lead Database, Duplicate Detection | §13-22 |
| **4** | Website Analysis, Social Research, Qualification | §23-28 |
| **5** | PRD Generator, PRD Review, AI PRD Chat, Version History | §29-34 |
| **6** | Demo Management, Demo Mapping | §35-38 |
| **7** | Outreach, Conversations, Follow-Ups, Sales, Pricing, Discounts | §39-57 |
| **8** | Performance, Correction, Analytics, Advanced Automation | §78-90 |

Each subsequent phase builds on the previous and will have its own detailed plan before execution.
