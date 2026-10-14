# Step-by-Step Render Deployment Guide

This guide walks you through deploying the AI Website Sales Automation Agent to **Render** using the Blueprint specification (`render.yaml`).

---

## Prerequisites

Before starting, ensure you have:
1. A **GitHub** account and the codebase pushed to a repository (private or public).
2. A **Render** account (linked to your GitHub account).
3. A **GitHub Personal Access Token (PAT)** with repository commit access (needed for compiling/publishing demo landing pages).

---

## Step 1: Generate your Encryption Key

APICredentials (like Google Maps API keys or GitHub tokens) are encrypted before being saved to the database. You must generate a Fernet symmetric encryption key to configure in Render's environment.

Run this command in your local terminal:
```bash
flask generate-key
```
**Copy the generated key**. It looks like this: `gAAAAABm...`. Keep this key safe.

---

## Step 2: Deploy to Render using Blueprints

Render's Blueprints automatically spin up both the **PostgreSQL Database** and the **Python Flask Web Service** and link them together.

1. Log in to the [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** in the top-right corner, and select **Blueprint**.
3. Under **Connect a repository**, select your repository from the list (or connect your GitHub account if you haven't already).
4. Fill out the Blueprint configuration form:
   * **Service Group Name**: `flixora-agent-group`
   * **Branch**: `main` (or whichever branch you pushed your code to)
5. Under **Environment Variables**, Render will prompt you for the following values:
   * `ENCRYPTION_KEY`: Paste the Fernet key you generated in **Step 1**.
   * `GITHUB_TOKEN`: Your GitHub Personal Access Token (PAT).
   * `GITHUB_USERNAME`: Your GitHub account username.
   * `TEST_MODE`: Leave as `true` for testing mode, or change to `false` for live mode.
6. Click **Apply**.

Render will now create the PostgreSQL database and build/start your web service.

---

## Step 3: Database Initialization (Automatic)

The Blueprint automatically runs `flask init-db` on startup:
* Creates the database tables in PostgreSQL.
* Seeds default settings and LLM configuration providers.
* Creates the default admin account.

---

## Step 4: First Login & Security Configuration

Once the deployment completes and the logs show `Running on http://0.0.0.0...`:

1. Navigate to your app's live URL: `https://flixora-sales-agent.onrender.com/`.
2. You will be redirected to the secure login page (`/login`).
3. Log in with the default credentials:
   * **Username**: `admin`
   * **Password**: `admin`
4. **Change your password immediately**:
   * Navigate to **Settings** -> **Profile**.
   * Fill out the **Change Password** form to secure the admin panel.

---

## Step 5: Post-Deployment Verification

Verify your live services are running correctly:
1. **Health check**: Go to `https://YOUR-APP.onrender.com/health`. It should return:
   ```json
   {
     "status": "healthy",
     "database": "connected"
   }
   ```
2. **Settings**: Go to **Settings** -> **Integrations** to confirm your Google Maps, GitHub, and WhatsApp statuses show configured.
3. **Run a test discovery**:
   * Go to **Leads** -> **Lead Discovery**.
   * Search for a category (e.g. `dentist` in `New York`) to verify the automated places search, contact scraping, scoring, and dossier compilation pipeline executes successfully.
