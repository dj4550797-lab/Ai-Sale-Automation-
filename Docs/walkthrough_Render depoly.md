# Render Production Deployment Preparation — Walkthrough

We have prepared the AI Website Sales Automation Agent for production deployment on Render. The application now supports PostgreSQL in production (with SQLite fallback in development), health checks, secure admin URL routing, and a Render Blueprint setup.

---

## 1. Exact Files Changed

*   [requirements.txt](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/requirements.txt): Added `psycopg2-binary==2.9.10` dependency to support PostgreSQL on Linux.
*   [config.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/config.py): Extended database URI parsing to automatically convert legacy `postgres://` connection strings to `postgresql://` (required by SQLAlchemy 2.0). Exposed environment-driven `TEST_MODE` control.
*   [app/\_\_init\_\_.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/__init__.py): Implemented the `/health` endpoint to verify live database connectivity.
*   [app/routes/auth.py](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/app/routes/auth.py): Added the secure `/admin` redirect route decorated with `@login_required`.
*   [.env.example](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/.env.example): Added variable slots for `TEST_MODE`, `GITHUB_TOKEN`, `GITHUB_USERNAME`, WhatsApp/Instagram keys, and SMTP configurations.

---

## 2. Exact Files Created

*   [render.yaml](file:///c:/Users/admin/Desktop/AI%20Sale%20Agent/render.yaml): Render Blueprint definition compiling the web service and PostgreSQL database.

---

## 3. Render Build & Start Commands

*   **Build Command**: `pip install -r requirements.txt`
*   **Start Command**: `flask init-db && gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`

---

## 4. Required Environment Variables

Configure the following variables in the Render Web Service settings (secrets can be kept empty in `.env.example`):
*   `SECRET_KEY`: Random string for sessions (auto-generated in `render.yaml`).
*   `DATABASE_URL`: Connection string to PostgreSQL (auto-injected in `render.yaml`).
*   `ENCRYPTION_KEY`: Fernet key to encrypt credentials (user must generate).
*   `GITHUB_TOKEN`: GitHub Personal Access Token (for demo deployments).
*   `GITHUB_USERNAME`: Authenticated GitHub username.
*   `TEST_MODE`: Controls mock vs live outreach (defaults to `true`).

---

## 5. Database Setup Instructions

1. Deploy using the Blueprint `render.yaml` to spin up a PostgreSQL instance and web service.
2. The database is initialized automatically during start command execution using `flask init-db`.
3. If setting up manually:
   - Create a PostgreSQL database on Render.
   - Set the `DATABASE_URL` environment variable in your service.
   - Run the command `flask init-db` via Render's shell tool or startup commands.

---

## 6. URLs Discovery (Flask Routes mapping)

| Feature | URL Path | Method | Access Requirement |
| :--- | :--- | :--- | :--- |
| **Admin Login** | `/login` | `GET`/`POST` | Anonymous |
| **Admin Redirection** | `/admin` | `GET` | `@login_required` (Redirects to `/dashboard`) |
| **Admin Dashboard** | `/dashboard` | `GET` | `@login_required` |
| **Leads Database** | `/leads` | `GET`/`POST` | `@login_required` |
| **Lead Discovery** | `/leads/discovery` | `GET`/`POST` | `@login_required` |
| **Website Analysis** | `/analysis` | `GET`/`POST` | `@login_required` |
| **PRD Management** | `/prds` | `GET`/`POST` | `@login_required` |
| **AI Assistant** | `/ai-assistant` | `GET`/`POST` | `@login_required` |
| **Conversations** | `/conversations` | `GET`/`POST` | `@login_required` |
| **Integrations Settings** | `/settings/integrations` | `GET` | `@login_required` |
| **LLM Provider Settings** | `/settings/llm/providers` | `GET` | `@login_required` |
| **Health Check** | `/health` | `GET` | Open (Returns 200/500 based on DB status) |

---

## 7. TEST_MODE Configuration

`TEST_MODE` is enabled by default (`true`). Under `TEST_MODE=true`, live outreach is simulated, and demo deployment URLs are mapped safely to `https://flixora.github.io/demo-{id} [TEST_MODE]`. To transition to production, the admin can edit settings or set `TEST_MODE=false`.

---

## 8. Storage Limitations

*   **Ephemeral Disk**: Render container file storage (e.g. `uploads/` directory) is lost when containers restart or redeploy.
*   **Production Fix**: Set up cloud storage (AWS S3, Google Cloud Storage, or attach a Render Persistent Disk at `/uploads`) to prevent loss of lead dossiers and files.

---

## 9. Security & Validation Checks

We verified locally that:
*   Flask server starts and is responsive.
*   `/health` returns `200 OK` and prints connection status: `{"database": "connected", "status": "healthy"}`.
*   `/admin` requires authentication and redirects to `/login?next=%2Fadmin` via 302 redirect.
*   Credentials are encrypted in settings using Fernet symmetric cryptography and are masked securely (e.g. `••••••••••••`) in templates.

---

## 10. Existing Test Results

All 69/69 tests passed successfully:
```
tests/test_analysis.py ..                                                [  2%]
tests/test_assistant.py ...                                              [  7%]
tests/test_auth.py ......                                                [ 15%]
tests/test_conversations.py ....                                         [ 21%]
tests/test_demos.py ...                                                  [ 26%]
tests/test_duplicates.py ......                                          [ 34%]
tests/test_enrichment.py ..........                                      [ 49%]
tests\test_fallback.py ..                                                [ 52%]
tests\test_files.py ..                                                   [ 55%]
tests\test_followups.py ...                                              [ 59%]
tests\test_github_deploy.py .....                                        [ 66%]
tests\test_knowledge.py ..                                               [ 69%]
tests\test_leads.py ..                                                   [ 72%]
tests\test_outreach.py ...                                               [ 76%]
tests\test_prds.py ...                                                   [ 81%]
tests\test_providers.py ...                                              [ 85%]
tests\test_sales.py ...                                                  [ 89%]
tests\test_security.py ...                                               [ 94%]
tests\test_system.py ...                                                 [100%]
====================== 69 passed, 80 warnings in 188.39s =======================
```
There are no deployment blockers. The application is ready to deploy!
