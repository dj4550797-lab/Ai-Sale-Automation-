# Phase 2 — Task Tracker

## LLM Configuration Services & Adapters
- [x] `app/integrations/llm/base.py` — Base adapter interface
- [x] `app/integrations/llm/openai_compatible.py` — OpenAI-compatible client integration
- [x] `app/integrations/llm/google_ai.py` — Gemini client integration
- [x] `app/services/llm_service.py` — Providers/models query and config service

## AI Fallback & Routing Engine
- [x] `app/ai/fallback_manager.py` — Priority fallback algorithm
- [x] `app/ai/llm_router.py` — Target route capability wrapper

## Route Blueprints
- [x] `app/routes/providers.py` — Replaces stub with full provider CRUD + API key setup
- [x] `app/routes/models.py` — Provider models management
- [x] `app/routes/credentials_api.py` — API testing and encrypted save routes

## Frontend Templates
- [x] `app/templates/settings/providers.html` — List providers, add provider modal, connection test results
- [x] `app/templates/settings/models.html` — Add/edit model, capability flags
- [x] Link credential tests on `app/templates/settings/integrations.html`

## Verification
- [x] Automated tests: `tests/test_providers.py` and `tests/test_fallback.py`
- [x] Manual verification via dashboard / settings
