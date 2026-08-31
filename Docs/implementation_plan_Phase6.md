# Phase 6 — Files & Demo Management

This plan covers the implementation of the **File Management** CRUD system, **Image Understanding (Vision)** analysis service, and **Demo Website Generator & Publisher** (§74, §75, §37, §38).

---

## User Review Required

> [!IMPORTANT]
> **Static Demo generation**:
> The personalized single-file `index.html` demo landing page will be compiled by calling the LLM router with the approved `PRD` sections as context. 
> The prompt will command the LLM to return a complete, standalone `index.html` document including embedded responsive CSS rules (matching visual typography and color directions) and basic interactive Javascript flows (such as contact submission modal popups and smooth scroll effects).
>
> **GitHub Pages Publishing Flow**:
> - In `TEST_MODE = True`, publishing a demo will bypass remote GitHub API integrations and instantly set the database entry status to published, returning a simulated deployment URL: `https://flixora.github.io/demo-<lead_id>`.
> - In `TEST_MODE = False`, it will save the file and optionally commit it to a configured static hosting site or GitHub repo using credentials entered in Settings.
>
> **Vision Model Mocking**:
> To support vision-based details extraction from uploaded business assets (e.g. logos, shopfront photos), the service will analyze image metadata. If the selected model does not support Vision or `TEST_MODE` is active, it will fall back to returning a structured simulated list of extracted colors, brand styles, and text elements.

---

## Open Questions

None. The database fields for `UploadedFile` and `DemoProject` match the requirements.

---

## Proposed Changes

### 1. Services

#### [NEW] [app/services/file_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/file_service.py)
Implements file uploading metadata storage:
- `save_uploaded_file(file, file_type='document', lead_id=None, prd_id=None, user_id=None)`
- `delete_uploaded_file(file_id)`
- `rename_uploaded_file(file_id, new_name)`

#### [NEW] [app/services/vision_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/vision_service.py)
Orchestrates image understand extraction:
- `analyze_business_image(file_id)`: Extracts color schemes, text headings, and brand guidelines from uploaded logo/asset files.
- Updates the lead's visual description styles or appends findings to context.

#### [NEW] [app/services/demo_service.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/services/demo_service.py)
Orchestrates single-file demo compilation:
- `compile_demo_html(lead_id)`: Prompts the Fallback Router to build a fully styled, single-file responsive landing page `index.html` based on the approved PRD text.
- Saves generated markup to local folders `uploads/demos/<lead_id>/index.html`.
- `publish_demo_project(lead_id)`: Mocks GitHub deployment URL mapping and runs validators to check if url is reachable (§38).

---

### 2. Route Blueprints

#### [NEW] [app/routes/files.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/files.py)
Exposes file CRUD controls:
- `GET /files` — List files categorized by type (Images, Logos, Documents) with search.
- `POST /files/upload` — Upload files via forms.
- `POST /files/delete/<int:id>` — Delete files.
- `POST /files/rename/<int:id>` — Rename metadata.
- `POST /files/analyze/<int:id>` — Trigger vision image analysis.

#### [NEW] [app/routes/demos.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/demos.py)
Exposes demo management routes:
- `GET /demos` — Display leads list with mapping states (No PRD, PRD Pending, Demo ready, Published).
- `POST /demos/generate/<int:lead_id>` — Trigger single-file landing page generation.
- `POST /demos/publish/<int:lead_id>` — Trigger publishing deployment flow.
- `GET /demos/preview/<int:lead_id>` — Server local preview route rendering the lead's generated `index.html`.

#### [MODIFY] [app/routes/stubs.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/stubs.py)
- Delete stubs for `demos_bp` and `files_bp`.

#### [MODIFY] [app/routes/__init__.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/__init__.py)
- Import and register actual `files_bp` and `demos_bp`.

---

### 3. Frontend Interface Templates

#### [NEW] [app/templates/files/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/files/index.html)
Folder explorer dashboard:
- Upload drag-and-drop zone.
- Visual thumbnail cards for images/logos.
- Clickable action cards to trigger image analysis or view results dialogs.

#### [NEW] [app/templates/demos/index.html](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/templates/demos/index.html)
Personalized demo workspace:
- Leads list with progress state badges (e.g. *Approved PRD Required*).
- One-click compile button.
- Preview and Publish buttons.
- Reachability status check indicator lamps.

---

## Verification Plan

### Automated Tests
1. **File Uploads & Vision Tests (`tests/test_files.py`)**:
   - Verify file save, type classifications, and database record mappings.
   - Verify image analyzer returns brand styles and hex codes.
2. **Demo Generation & Deployment Tests (`tests/test_demos.py`)**:
   - Verify HTML compiler parses PRD into a single index page.
   - Verify validators check reachable states and publish URLs.
   - Execute:
     ```bash
     venv\Scripts\pytest tests/test_files.py tests/test_demos.py
     ```

### Manual Verification
1. Upload a business logo. Click **Analyze Image** and confirm it extracts dominant colors (e.g. *Dark Gold, Light Beige*).
2. Go to **Demos**, select a lead with an approved PRD, and click **Compile Demo**.
3. Click **Preview Demo** to verify the responsive styling.
4. Click **Publish Demo**, and verify the live deployment URL.
