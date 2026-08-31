# Phase 3 — Lead Discovery, Lead Database & Duplicate Detection

## Goal Description
Implement the complete Lead Discovery engine, Lead Database view, and Duplicate Detection logic. This includes integrating the new Google Places API (Text Search and Place Details) with dynamic field masks to fetch local business leads safely, scoring them, and detecting duplicates. We will also seed the user-configured OpenRouter and Google Gemini models as requested.

---

## User Review Required

> [!IMPORTANT]
> **LLM Seeding Config:** We will update the default seeding logic (`flask init-db`) to register the following as requested:
> - **Provider:** `openrouter` (OpenRouter Primary) with base URL `https://openrouter.ai/api/v1` and models:
>   - `openai/gpt-4o-mini` (Priority 1)
>   - `google/gemini-2.0-flash-exp:free` (Priority 2)
> - **Multiple Provider/Account Fallbacks:** We will pre-configure placeholders for 3 premium Google AI Studio accounts (`google_ai_1`, `google_ai_2`, `google_ai_3`) with separate credentials, so that fallback router automatically cycles through them if one is down or rate-limited.
>
> **Google Places API Integration:**
> Lead discovery requires a Google Places API key. We will implement `BusinessDataProvider` abstraction using the New Google Places API. We will use the field mask `places.id,places.displayName,places.primaryType,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount` to fetch only necessary data to minimize costs (§15).

---

## Open Questions

None. The duplicate detection criteria match PRD §22.

---

## Proposed Changes

### LLM Seeding Update

#### [MODIFY] [app/__init__.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/__init__.py)
Update `_seed_defaults(db)` to:
- Seed provider `openrouter` (OpenRouter Primary) with base URL `https://openrouter.ai/api/v1`
- Seed models `openai/gpt-4o-mini` and `google/gemini-2.0-flash-exp:free` linked to `openrouter`
- Seed 3 fallback Google AI Studio provider accounts (`google_ai_1`, `google_ai_2`, `google_ai_3`) to facilitate multi-provider account redundancy (§63-64).

---

### Lead Discovery & Google Places API Adapter

#### [NEW] [integrations/maps/base.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/integrations/maps/base.py)
Define the `BusinessDataProvider` interface (§103):
- `search_businesses(location, category, limit)`
- `get_business_details(place_id)`

#### [NEW] [integrations/maps/google_places.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/integrations/maps/google_places.py)
Google Places API (New) adapter using Text Search and Place Details endpoints. Uses field masks for Places API New, parsing and mapping responses into independent business fields.

#### [NEW] [services/lead_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/lead_service.py)
Orchestrates Lead Discovery:
- Invokes Maps integration
- Normalizes business details
- Executes Duplicate Detection
- Persists leads and logs run history

#### [NEW] [utils/duplicate_detector.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/utils/duplicate_detector.py)
Implements duplicate matching matching PRD §22:
- First-level match: Google Place ID
- Second-level match: Phone + Address, Website, or Business Name + Address
- Returns matching verdict: `unique`, `likely_duplicate`, or `confirmed_duplicate`.

---

### Route Changes

#### [MODIFY] [routes/leads.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/leads.py)
Replace stub with lead routes:
- `GET /leads` — List leads with filters (Location, Category, Rating, Score, Status) and search
- `GET /leads/<id>` — Lead detail view showing business, contact, reputation, and website details (§20)
- `GET /leads/discover` — Discover form (Location, Category, Target, Priority, Website Required, Min Rating)
- `POST /leads/discover` — Launch discovery background job and return process status/count (§14)

---

### Frontend Views

#### [NEW] [templates/leads/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/leads/index.html)
Leads table displaying columns: Business, Category, Location, Phone, Website, Instagram, Rating, Reviews, Lead Score, Status, Demo, Last Action (§19). Mobile-responsive (collapses to cards).

#### [NEW] [templates/leads/discover.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/leads/discover.html)
Form for location, category, daily target. Includes:
- **Start Lead Discovery confirmation dialog** (§14)
- **Progress bar / Spinner UI** updating lead discover state dynamically (§14, §135)

#### [NEW] [templates/leads/detail.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/leads/detail.html)
Clean structured lead details page (§20) showing separated tabs for Business Details, Reputation, Activity logs, and Qualification indicators.

---

## Verification Plan

### Automated Tests
- Run `python -m pytest tests/test_duplicates.py` to cover Place ID matching, phone/address matches, and confirmed duplicate states.
- Run `python -m pytest tests/test_leads.py` to cover lead list filtering, search, and details views.

### Manual Verification
1. Access Lead Discovery form. Search for "Salon" in "Delhi" with target 5.
2. Confirm dialog shows search details.
3. Start discovery and check progress spinner.
4. Verify leads list displays rating, reviews, website URI, and place details.
