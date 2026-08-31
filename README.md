# Flixora AI Sales Automation Agent

AI-powered internal sales automation platform for local-business website sales.

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy environment template
cp .env.example .env

# Generate encryption key
flask generate-key
# Add the output to .env as ENCRYPTION_KEY
```

Edit `.env` with your settings.

### 3. Initialize Database

```bash
flask init-db
```

### 4. Run

```bash
python app.py
```

Visit `http://127.0.0.1:5000`

Default login: `admin` / `admin123`

## Tech Stack

- **Backend:** Python 3.12, Flask, SQLAlchemy, Gunicorn
- **Frontend:** HTML5, CSS3, JavaScript, Material Design 3
- **Database:** SQLite (dev), PostgreSQL (production)
- **AI:** Multi-provider LLM orchestration with fallback routing
- **Security:** Fernet encryption, CSRF, rate limiting, audit logging

## Project Structure

```
app/
├── models/        # Database models (SQLAlchemy)
├── routes/        # Flask route blueprints
├── services/      # Business logic
├── agents/        # AI task orchestration
├── ai/            # LLM infrastructure
├── integrations/  # External API adapters
├── automation/    # Scheduled jobs
├── security/      # Auth, encryption, validation
├── templates/     # Jinja2 HTML templates
├── static/        # CSS, JS, images
├── schemas/       # Pydantic validation
├── prompts/       # AI prompt templates
└── utils/         # Helpers, logging, time
```

## Development Phases

1. ✅ Foundation (Flask, DB, Auth, UI Shell, Settings)
2. ⬜ LLM Provider Manager, Model Manager, Fallback Router
3. ⬜ Lead Discovery, Lead Database, Duplicate Detection
4. ⬜ Website Analysis, Social Research, Qualification
5. ⬜ PRD Generator, PRD Review, AI PRD Chat
6. ⬜ Demo Management, Demo Mapping
7. ⬜ Outreach, Conversations, Follow-Ups, Sales
8. ⬜ Performance, Correction, Analytics, Automation

## License

Proprietary — Flixora
