# Phase 4 — Website Opportunity Analysis & PRD Generator

This plan covers the implementation of the **Website Opportunity Analysis** engine and the **AI PRD Generator** module. 
These modules allow Flixora to analyze prospect websites for structural design issues (Visual, Mobile, Navigation, CTA, Performance) and automatically generate version-controlled Product Requirements Documents (PRDs) detailing custom website improvements/solutions.

---

## User Review Required

> [!IMPORTANT]
> **Scraping / Crawling Policy in `TEST_MODE`**:
> To ensure test suite reliability, when `TEST_MODE = True`, the scraping module will bypass actual external network HTTP requests and instead return simulated structural website profiles based on the target lead's category. When `TEST_MODE = False`, it will perform basic HTTP GET requests to retrieve the page body, parsing out metadata, layout semantics, and anchor links.
>
> **PRD Generation Prompts**:
> The PRD generation will utilize a structured prompt targeting the 10 core fields in `PRD` (§31):
> 1. Business Overview
> 2. Business Analysis
> 3. Website Goal
> 4. Target Audience
> 5. Design Direction
> 6. Site Structure
> 7. Functional Requirements
> 8. Content Requirements
> 9. CTA Strategy
> 10. Technical Requirements

---

## Open Questions

None. The schema definitions, criteria items (§26), and status triggers align fully with PRD guidelines.

---

## Proposed Changes

### 1. Website Analysis & Scraper Engine

#### [NEW] [app/services/scraper_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/scraper_service.py)
Implements a scraper client to parse external website content:
- Bypasses real network fetches when `current_app.config['TEST_MODE']` is enabled.
- Normalizes HTML tags to extract headings, links, and forms.

#### [NEW] [app/services/analysis_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/analysis_service.py)
Orchestrates website analyses:
- Triggers LLM router completions matching the criteria outlined in PRD §26 (Visual Design, Layout, Typography, Branding, Mobile, Navigation, CTA, Contact Flow, Service Presentation, Trust Signals, Performance Signals, Basic Accessibility, Conversion).
- Saves scores (0–100) per criterion.
- Separates findings into three distinct arrays inside the database JSON fields: `observed_facts`, `ai_recommendations`, and `ai_inferences` to prevent AI hallucinations (§862-868).
- Saves verdict (`adequate`, `needs_improvement`, `no_website`).

---

### 2. PRD Generator & Chat Services

#### [NEW] [app/services/prd_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/prd_service.py)
Orchestrates PRD generation and version control:
- Generates/regenerates a PRD using the Priority Fallback LLM Router.
- For leads with no website: Automatically creates a **New Website PRD** (§1009).
- For leads with an existing website: Creates an **Improvement PRD** if `improvement_needed` is `True` (§983); skips if `False` (§995).
- Saves all revisions in `PRDVersion` snapshots using version increments.
- Implements `revise_prd_with_ai(prd_id, instruction)`: Revises relevant PRD markdown blocks based on admin chat directions (e.g. *"Make the visual style more premium"*), creating a new incremented version.

---

### 3. Route Blueprints

#### [NEW] [app/routes/analysis.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/analysis.py)
Exposes endpoint controls for website analyses:
- `POST /analysis/run/<int:lead_id>` — Trigger background or immediate analysis of the website.
- `GET /analysis/<int:lead_id>` — Display analysis scores card, breakdown grid, and lists of observed facts, inferences, and recommendations.

#### [NEW] [app/routes/prds.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/prds.py)
Exposes management routes for PRD drafts:
- `GET /prds` — Render table of PRD drafts, showing statuses (`DRAFT`, `UNDER REVIEW`, `APPROVED`, etc.).
- `GET /prds/<int:id>` — Detail panel rendering core text components, version history dropdown list, and approve/reject/regenerate action triggers.
- `POST /prds/<int:id>/action` — Handle status transition buttons (`Approve`, `Reject`).
- `POST /prds/<int:id>/chat` — Handle AJAX chat submission for AI-driven PRD updates.
- `GET /prds/<int:id>/compare` — View side-by-side diff comparing two versions.

#### [MODIFY] [app/routes/stubs.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/stubs.py)
- Remove `analysis_bp` and `prds_bp` stubs.

#### [MODIFY] [app/routes/__init__.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/__init__.py)
- Register actual `analysis_bp` and `prds_bp` blueprints.

---

### 4. Frontend Interface Templates

#### [NEW] [app/templates/analysis/detail.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/analysis/detail.html)
Displays website analysis scorecard, rating breakdown sliders, and separate tabs for Observed Facts, AI Inferences, and AI Recommendations.

#### [NEW] [app/templates/prds/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/prds/index.html)
List of prospects with generated PRD cards showing statuses, scores, and timestamps.

#### [NEW] [app/templates/prds/detail.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/prds/detail.html)
Rich split-layout view (§31):
- **Left Column**: Structured PRD section cards (Business Overview, Site Structure, functional rules) with action buttons (Approve/Reject).
- **Right Column (Chat Drawer)**: Chat history feed allowing the Admin to type instructions ("Ask AI") to refine the copy.
- **Version Modal**: Dropdown selection showing diff comparison of revisions.

---

## Verification Plan

### Automated Tests
1. **Website Analysis Test Suite (`tests/test_analysis.py`)**:
   - Verify that triggers skip analysis when no website exists.
   - Verify scoring computations and JSON structures.
2. **PRD Generation & Revision Suite (`tests/test_prds.py`)**:
   - Verify that New Website PRD generates successfully for web-less leads.
   - Verify version incrementing and history snapshots.
   - Verify AI revision chat updates the database values correctly.
   - Execute:
     ```bash
     venv\Scripts\pytest tests/test_analysis.py tests/test_prds.py
     ```

### Manual Verification
1. Log in and open a lead with an existing website.
2. Click **Run Website Analysis** and watch the score breakdown update.
3. Open a PRD draft, click **Ask AI** in the chat drawer, type *"Make the design direction mobile-first"*, and check that the layout updates with an incremented version number.
4. Approve the PRD and confirm status transitions to `APPROVED`.
