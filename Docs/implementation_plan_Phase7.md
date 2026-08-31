# Phase 7 — Outreach, Follow-ups, & Sales Pipeline

This plan covers the implementation of the **Outreach Campaigns** panel, the **Follow-ups Scheduler** with automated cron jobs and stop conditions, and the **Sales Kanban Board Pipeline** (§39, §49, §50, §51, §52).

---

## User Review Required

> [!IMPORTANT]
> **Outreach Channels & TEST_MODE**:
> The system will support 3 outreach channels: `email`, `whatsapp`, and `instagram`.
> - In `TEST_MODE = True`, pings will be simulated and logged in the database table (`OutreachEvent` logs), skipping real network deliveries but transitioning lead status to `CONTACTED`.
> - In `TEST_MODE = False`, it runs corresponding isolated messaging adapters.
>
> **Sales Pipeline Integration**:
> To ensure lead states and sales deals remain perfectly synced, modifying a `SalesDeal` kanban stage will automatically trigger a cascading update to its corresponding `Lead.status` property (§52).
>
> **Cron Follow-ups Engine**:
> Automated follow-ups run sequentially (e.g. initial -> delay -> follow-up 1 -> delay -> follow-up 2 -> stop) up to a configurable maximum count. Any incoming reply or deal progress will immediately update the follow-up record to `CANCELLED` with a recorded `stop_reason` (§51).

---

## Open Questions

None. The database structures align with the kanban stage enums.

---

## Proposed Changes

### 1. Services

#### [NEW] [app/services/outreach_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/outreach_service.py)
Implements messaging pitch logic:
- `generate_outreach_message(lead_id, channel)`: Compiles custom greeting, link, and CTA based on the approved PRD and demo.
- `send_outreach_campaign(campaign_id)`: Dispatches messages, registers delivery events, and updates lead to `CONTACTED`.
- `simulate_incoming_reply(lead_id, reply_content)`: Registers replies, sets campaign to `REPLIED`, and triggers human notification.

#### [NEW] [app/services/followup_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/followup_service.py)
Implements sequence timers and stop conditions:
- `schedule_next_followup(lead_id, outreach_id, followup_number=1, delay_days=3)`: Creates a scheduled follow-up.
- `process_followups_cron()`: Scans scheduled items, cancels them if stop conditions are met (§51), compiles follow-up text, and sends pings.

#### [NEW] [app/services/sales_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/sales_service.py)
Implements sales pipeline aggregates:
- `get_deals_by_stage()`: Maps sales deals into kanban stages dictionary.
- `update_deal_stage(deal_id, to_stage, deal_value=None, lost_reason=None)`: Transitions deal stage, logs history events, and syncs lead status.

---

### 2. Route Blueprints

#### [NEW] [app/routes/outreach.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/outreach.py)
Exposes outreach campaign lists and actions:
- `GET /outreach` — List all campaigns with filters.
- `POST /outreach/prepare/<int:lead_id>` — Initialize and compile message draft.
- `POST /outreach/send/<int:campaign_id>` — Execute sending.
- `POST /outreach/simulate-reply/<int:lead_id>` — Simulation helper for client replies.

#### [NEW] [app/routes/followups.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/followups.py)
Exposes follow-up schedules:
- `GET /followups` — List scheduled, sent, and cancelled follow-ups (§49).
- `POST /followups/trigger-cron` — Manual endpoint to trigger the follow-up cron job.

#### [NEW] [app/routes/sales.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/sales.py)
Exposes Kanban board:
- `GET /sales` — Display Deals board columns (§52).
- `POST /sales/transition/<int:deal_id>` — Transition stages, update value, or apply won/lost states.

#### [MODIFY] [app/routes/stubs.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/stubs.py)
- Delete stubs for `outreach_bp`, `followups_bp`, and `sales_bp`.

#### [MODIFY] [app/routes/__init__.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/__init__.py)
- Import and register actual blueprints.

---

### 3. Frontend Interface Templates

#### [NEW] [app/templates/outreach/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/outreach/index.html)
List explorer and messaging preview overlay:
- Table listing prospects, channels, and message preview snippets.
- Interactive modal showing complete message text, enabling direct inline edits before sending (§41).

#### [NEW] [app/templates/followups/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/followups/index.html)
Timeline status index rendering Lead, Last Contact, Follow-up #, Scheduled Time, and Status details (§49).

#### [NEW] [app/templates/sales/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/sales/index.html)
Visual Kanban Dashboard:
- Columns for NEW, CONTACTED, REPLIED, INTERESTED, NEGOTIATION, WON, LOST stages.
- Card elements showing prospect name, deal value, and pricing plan details.
- Edit Value modals and Won/Lost reason overlays.

---

## Verification Plan

### Automated Tests
1. **Outreach & Pipeline Tests (`tests/test_outreach.py`)**:
   - Verify personalized message compilations.
   - Verify campaigns saving and client reply simulation flows.
2. **Follow-ups Sequence Tests (`tests/test_followups.py`)**:
   - Verify scheduler delays and cron iterations.
   - Verify stop conditions (replies, deal won/lost states cancel follow-ups).
3. **Kanban stage syncs (`tests/test_sales.py`)**:
   - Verify transitioning deal stages syncs lead status.
   - Execute:
     ```bash
     venv\Scripts\pytest tests/test_outreach.py tests/test_followups.py tests/test_sales.py
     ```

### Manual Verification
1. Open **Outreach**, select a prospect, and click **Prepare Outreach**. Verify the preview dialog lists the generated links and text.
2. Open **Sales**, drag a prospect card to WON, and confirm the corresponding lead's status updates immediately.
3. Simulate a client reply on a prospect, and verify that their scheduled follow-up is immediately marked as cancelled.
