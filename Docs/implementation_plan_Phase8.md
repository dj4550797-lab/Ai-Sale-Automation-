# Phase 8 — Client Conversations & Human Takeover

This plan covers the implementation of the **Client Conversations panel**, the **Human Takeover toggle workflow**, and the **AI Chatbot responder** mapping company pricing rules and context isolation (§43, §44, §45, §46, §47, §48).

---

## User Review Required

> [!IMPORTANT]
> **Takeover Workflow & AI Toggle**:
> The system enables the admin to pause automated AI replies at any time:
> - `AI_ACTIVE` state: Automatic replies will be triggered whenever a client message is simulated or received.
> - `ADMIN_ACTIVE` state: Automatic replies are disabled. The admin can text manually.
> - Clicking "Take Over" shows a modal warning dialog (§45).
>
> **Retrieval-Augmented Chatbot Responder**:
> The client-facing AI replies using a custom agent persona based on Agent Settings (category `agent`). It queries company knowledge (category `knowledge_base` entries where `is_enabled=True`) and catalog pricing structures to generate accurate answers and prevent hallucination (§46).
>
> **Conversation & Context Isolation**:
> Each client session has its own message logs and context dictionary (`context_data` JSON field). Admin-facing system chats are completely separated from client-facing conversations (§48).

---

## Open Questions

None. The database models `Conversation` and `Message` are already defined and align with these requirements.

---

## Proposed Changes

### 1. Services

#### [NEW] [app/services/conversation_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/conversation_service.py)
Implements context isolation and chatbot reply loops:
- `create_or_get_conversation(lead_id)`: Fetches or creates an isolated conversation log.
- `add_message(conversation_id, sender_type, content, sender_name='')`: Saves a message in the SQLite database.
- `generate_chatbot_reply(conversation_id, user_message)`: Combines Agent persona configuration, pricing plan options, and enabled knowledge base FAQs to prompt the LLM Router.
- `toggle_takeover_status(conversation_id, active, admin_user_id)`: Sets conversation status to `ADMIN_ACTIVE` or `AI_ACTIVE`.

---

### 2. Route Blueprints

#### [NEW] [app/routes/conversations.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/conversations.py)
Exposes client conversation timelines and admin controls:
- `GET /conversations` — Double-panel chat window showing active clients on the left, message histories and toggles on the right.
- `POST /conversations/takeover/<int:conversation_id>` — Toggle takeover states.
- `POST /conversations/reply/<int:conversation_id>` — Manual admin text response.
- `POST /conversations/simulate-client/<int:conversation_id>` — Mocks incoming customer pings to verify chatbot replies.

#### [MODIFY] [app/routes/stubs.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/stubs.py)
- Delete stubs for `conversations_bp`.

#### [MODIFY] [app/routes/__init__.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/__init__.py)
- Import and register actual `conversations_bp` route.

---

### 3. Frontend Interface Templates

#### [NEW] [app/templates/conversations/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/conversations/index.html)
Interactive Split-Panel UI:
- **Left Panel**: Scrollable client cards detailing company name, category, and status indicators.
- **Right Panel Header**: Active status banner (`AI ACTIVE` / `ADMIN ACTIVE`) and Takeover action button.
- **Right Panel Body**: Chat message thread (rendered left-aligned for clients, right-aligned for Admin/AI).
- **Right Panel Footer**: Textarea for manual responses, and a special toggle tab to send simulated client messages for quick testing.

---

## Verification Plan

### Automated Tests
1. **Conversations & Takeover Tests (`tests/test_conversations.py`)**:
   - Verify isolated conversation creation.
   - Verify automated chatbot retrieves knowledge FAQ rules and active pricing.
   - Verify taking over pauses automatic AI replies.
   - Execute:
     ```bash
     venv\Scripts\pytest tests/test_conversations.py
     ```

### Manual Verification
1. Open **Conversations** and select a client.
2. Under the simulation panel, type *"How much does this cost?"* and verify that the AI replies automatically with correct pricing figures.
3. Click **Take Over**, confirm the modal prompt, and verify the status shifts to `ADMIN_ACTIVE`.
4. Send another simulated message and confirm that the AI remains silent. Type an admin reply and verify it delivers.
