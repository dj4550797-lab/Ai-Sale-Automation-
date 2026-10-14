# Phase 2 — LLM Providers & Fallback Router

## Goal Description
Implement the complete LLM configuration, management, and fallback routing infrastructure. This enablesflixora to support dynamic model selections, secure API credential storage, and seamless fallback routing across provider accounts if timeouts or rate limits occur.

---

## User Review Required

> [!IMPORTANT]
> **Key Protocols:** We will support three primary protocols in Phase 2:
> 1. **OpenAI Compatible** (for OpenRouter, Local LLMs, etc.)
> 2. **Gemini** (for Google AI)
> 3. **Anthropic Compatible**
>
> **Task Routing & Capabilities:** Models will be tagged with capabilities (`text`, `vision`, `tool_calling`, `structured_output`). The Fallback Router will filter models to match the capability required by the AI task (§130) and prioritize by user-defined order.

---

## Open Questions

None at this time. The PRD specifications are clear.

---

## Proposed Changes

### Backend Infrastructure

#### [MODIFY] [routes/providers.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/providers.py)
Replace stub with provider routes:
- `GET /settings/llm/providers` — List all LLM providers and their models
- `POST /settings/llm/providers` — Add/edit LLM provider
- `POST /settings/llm/providers/<id>/delete` — Delete provider
- `POST /settings/llm/providers/<id>/toggle` — Enable/disable provider
- `POST /settings/llm/providers/<id>/test` — Test connection to the provider and retrieve available models

#### [NEW] [routes/models.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/models.py)
Create model management routes:
- `GET /settings/llm/providers/<provider_id>/models` — List models for a provider
- `POST /settings/llm/providers/<provider_id>/models` — Add/edit model details
- `POST /settings/llm/providers/<provider_id>/models/<id>/delete` — Delete model config
- `POST /settings/llm/providers/<provider_id>/models/<id>/toggle` — Toggle model active state

#### [NEW] [routes/credentials_api.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/credentials_api.py)
Integrations & credential testing routes:
- `POST /api/credentials/<id>/test` — Decrypt and test connection to Maps, LLM, or Messaging APIs (§98)
- `POST /api/credentials` — Securely encrypt and save key/token (§17)

#### [NEW] [services/llm_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/llm_service.py)
Handles business logic for LLM providers and models:
- Decrypting credentials at runtime (§18)
- Mapping model configuration records
- Refreshing provider status based on latency or failure counts

#### [NEW] [integrations/llm/base.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/integrations/llm/base.py)
Base adapter interface defining `generate_text()`, `generate_structured_output()`, and `test_connection()`.

#### [NEW] [integrations/llm/openai_compatible.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/integrations/llm/openai_compatible.py)
Integration with OpenAI compatible endpoints (OpenRouter, local servers, custom OpenAI endpoints).

#### [NEW] [integrations/llm/google_ai.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/integrations/llm/google_ai.py)
Integration with the Gemini API using HTTP requests or the `google-generativeai` package if appropriate.

#### [NEW] [ai/fallback_manager.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/ai/fallback_manager.py)
Logical router selecting the fallback path. Finds all active nodes (Provider + Model) matching capability needs, sorts them by priority, and executes them in sequence on failure.

#### [NEW] [ai/llm_router.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/ai/llm_router.py)
Entry point wrapper for tasks. Instead of calling specific APIs directly, services call `llm_router.generate(task_type, prompt, options)` which triggers `fallback_manager` internally.

---

### Templates & Frontend

#### [NEW] [templates/settings/providers.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/settings/providers.html)
List of LLM providers with cards showing online/offline status, model counts, and edit/delete/test controls (§133). Includes:
- **Add Provider Dialog** (§59)
- **Edit/Delete dialogs**

#### [NEW] [templates/settings/models.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/settings/models.html)
Model list for a specific provider showing capability flags (Text, Vision, Tools, JSON). Includes:
- **Add Model Dialog** (§62)

#### [MODIFY] [templates/settings/integrations.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/settings/integrations.html)
Link the integration credentials test button to the `/api/credentials/<id>/test` endpoint.

---

## Verification Plan

### Automated Tests
- Run `python -m pytest tests/test_providers.py` to verify:
  - Adding provider & credential encryption
  - Model capabilities mapping
  - Fallback logic (forcing a mock failure on first provider, verifying successful fallback to second provider)
- Run `python -m pytest tests/test_fallback.py` to test routing conditions.

### Manual Verification
1. Access LLM settings page. Add a dummy OpenAI-compatible provider.
2. Verify credentials mask in the list (`••••••••••••A91K`).
3. Add a model with capabilities text & structured output.
4. Verify dynamic status indicator matches the provider state.
