# Phase 5 — Knowledge Base & Admin AI Assistant

This plan covers the implementation of the **Knowledge Base** management CRUD system and the **Admin AI Assistant** chat interface with capability tool-access integration (§73, §76, §77).

---

## User Review Required

> [!IMPORTANT]
> **Admin Assistant Tool Execution**:
> The Admin AI Assistant needs to answer operational questions about the system (e.g. *"Show pending PRDs"*, *"How many leads were found today?"*). 
> We will implement a controlled tool dispatcher that parses the AI intent and invokes safe database queries/aggregators. We will support 7 key helper tools:
> 1. `get_lead_analytics()` (Lead counts, counts by category, counts by status)
> 2. `get_sales_analytics()` (Deals won, pipeline stage aggregates)
> 3. `search_prds(query)` (List PRD titles, status filtering)
> 4. `search_conversations(query)` (List ongoing threads, recent messages)
> 5. `lookup_pricing()` (List active plans)
> 6. `get_automation_status()` (Active jobs and recent run metrics)
> 7. `get_system_health()` (Active providers status and key latency flags)
>
> **LLM Provider for Assistant**:
> The assistant will run using the LLM Router's priority fallback logic, ensuring high availability of the chat assistant interface.

---

## Open Questions

None. The requirements align with standard SQL aggregations and the existing database models.

---

## Proposed Changes

### 1. Services

#### [NEW] [app/services/knowledge_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/knowledge_service.py)
Implements CRUD functions for the knowledge base:
- `create_kb_entry(category, title, content, is_enabled=True)`
- `update_kb_entry(entry_id, category, title, content, is_enabled)`
- `delete_kb_entry(entry_id)`
- `list_kb_entries(category=None)`

#### [NEW] [app/services/assistant_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/assistant_service.py)
Orchestrates AI assistant chat responses:
- Processes the chat message input.
- Classifies user intent to decide if one or more database tool functions should be executed.
- Formulates a context-rich prompt incorporating the query and the tool outputs.
- Calls `llm_router.generate_text` to formulate a friendly, professional response.

---

### 2. Route Blueprints

#### [NEW] [app/routes/knowledge.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/knowledge.py)
Exposes CRUD endpoints for knowledge base settings:
- `GET /knowledge` — Render categorized list of knowledge items.
- `POST /knowledge/add` — Add a new entry form submit.
- `POST /knowledge/edit/<int:id>` — Edit details.
- `POST /knowledge/delete/<int:id>` — Remove entry.
- `POST /knowledge/toggle/<int:id>` — Quick toggle enable/disable state (§73).

#### [NEW] [app/routes/ai_assistant.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/ai_assistant.py)
Exposes the Admin assistant panel:
- `GET /ai-assistant` — Render the fullscreen chat assistant workspace.
- `POST /ai-assistant/message` — Receive text messages and return generated replies via JSON.

#### [MODIFY] [app/routes/stubs.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/stubs.py)
- Delete stubs for `ai_assistant_bp` and `knowledge_bp`.

#### [MODIFY] [app/routes/__init__.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/__init__.py)
- Import and register actual `knowledge_bp` and `ai_assistant_bp`.

---

### 3. Frontend Interface Templates

#### [NEW] [app/templates/knowledge/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/knowledge/index.html)
Interactive management view containing:
- Sidebar tabs for KBCategory (Company, Services, Pricing, FAQs, Sales Rules, Policies, Agent Rules).
- Lists of entries with edit/delete modals.
- Toggle switches for enabling/disabling items immediately.

#### [NEW] [app/templates/ai_assistant/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/ai_assistant/index.html)
Fullscreen clean chat canvas containing:
- Message feed container.
- Textarea message input form.
- Predefined quick query action chips (e.g. *"Show pending PRDs"*, *"Leads discovered today"*).

---

## Verification Plan

### Automated Tests
1. **Knowledge Base Tests (`tests/test_knowledge.py`)**:
   - Verify CRUD database persistence.
   - Verify toggles update enabled states.
2. **AI Assistant Tests (`tests/test_assistant.py`)**:
   - Verify intent classification triggers correct database tool methods.
   - Verify analytics return counts accurately.
   - Execute:
     ```bash
     venv\Scripts\pytest tests/test_knowledge.py tests/test_assistant.py
     ```

### Manual Verification
1. Open **Knowledge Base** settings and create a test FAQ entry. Toggle it off, then verify it is marked as disabled in the database.
2. Open **AI Assistant** chat and type: *"How many leads were found today?"*. Confirm the agent responds with the count of leads discovered.
3. Click the chip *"Show pending PRDs"*, and confirm a list of drafts is returned.
