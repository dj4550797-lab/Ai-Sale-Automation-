"""
Flixora AI Sales Automation Agent — Demo Service

Generates single-page HTML demos and handles static hosting mapping (§37, §38).
"""
import os
import requests
from datetime import datetime, timezone
from flask import current_app

from app.extensions import db
from app.models import Lead, PRD, DemoProject, APICredential
from app.constants import PRDStatus, LeadStatus
from app.ai.llm_router import llm_router
from app.utils.logger import get_logger

logger = get_logger('services')


def compile_demo_html(lead_id):
    """
    Generate a personalized single-file index.html demo page for a lead based on their approved PRD.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return {"success": False, "error": f"Lead with ID {lead_id} not found."}

    # 1. Fetch approved PRD (§37)
    prd = PRD.query.filter_by(lead_id=lead_id, status=PRDStatus.APPROVED).first()
    if not prd:
        return {"success": False, "error": "An approved PRD is required before compiling the demo website. Please approve the draft in PRD Review."}

    logger.info(f"Compiling single-page demo website for: {lead.business_name}")

    # 2. Formulate Prompt to LLM to return complete standalone HTML
    prompt = f"""
    You are an elite web designer and frontend developer.
    Your task is to write a single-file, highly-polished, responsive website landing page (index.html) for:
    Business Name: {lead.business_name}
    Business Category: {lead.business_category}
    
    Here is the approved Product Requirements Document (PRD) to guide the layout:
    Title: {prd.title}
    Website Goal: {prd.website_goal}
    Design Direction: {prd.design_direction}
    Site Structure: {prd.site_structure}
    Functional Requirements: {prd.functional_requirements}
    CTA Strategy: {prd.cta_strategy}
    
    Guidelines:
    - Return a complete, self-contained HTML page including <!DOCTYPE html> and <html> tags.
    - Embed all CSS styling inside a <style> tag in the <head>. Use modern visual aesthetics (curated colors, sleek borders, smooth hover animations, modern typography).
    - Embed all JavaScript logic inside a <script> tag before the </body>. Add interactive effects (smooth scrolling, contact form modal popups, floating quick action triggers).
    - Do not output any markdown code blocks or wrapper text (do not start with ```html). Return only the raw HTML copy.
    """

    try:
        html_code = llm_router.generate_text(prompt, task_type='demo_generation')
        
        # Clean up code blocks if returned by model anyway
        if html_code.startswith("```"):
            lines = html_code.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            html_code = "\n".join(lines).strip()

        # 3. Save index.html to disk
        base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        demo_dir = os.path.join(base_upload, 'demos', str(lead_id))
        os.makedirs(demo_dir, exist_ok=True)
        file_path = os.path.join(demo_dir, 'index.html')
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_code)

        # 4. Create/update DemoProject record in DB
        demo = DemoProject.query.filter_by(lead_id=lead_id).first()
        preview_url = f"/demos/preview/{lead_id}"
        
        if not demo:
            demo = DemoProject(
                lead_id=lead_id,
                demo_name=f"Demo - {lead.business_name}",
                demo_url=preview_url,
                business_name=lead.business_name,
                url_valid=True,
                url_reachable=True,
                last_validated=datetime.now(timezone.utc)
            )
            db.session.add(demo)
        else:
            demo.demo_url = preview_url
            demo.url_valid = True
            demo.url_reachable = True
            demo.last_validated = datetime.now(timezone.utc)

        # Update lead status
        lead.status = LeadStatus.CONTACTED  # Move along sales funnel
        lead.last_action = "Demo website compiled"
        lead.last_action_at = datetime.now(timezone.utc)

        db.session.commit()
        logger.info(f"Demo website index.html generated successfully for lead {lead_id}.")
        return {"success": True, "demo_id": demo.id, "preview_url": preview_url}
        
    except Exception as e:
        logger.error(f"Error compiling demo website for lead {lead_id}: {e}")
        return {"success": False, "error": f"Demo compilation failed: {str(e)}"}


def publish_demo_project(lead_id):
    """
    Publish the compiled demo website to GitHub Pages or static host (§37).
    Maps the final live URL and runs validation pings.
    """
    demo = DemoProject.query.filter_by(lead_id=lead_id).first()
    if not demo:
        return {"success": False, "error": "No compiled demo website found to publish. Please compile it first."}

    # Verify physical file exists
    base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    file_path = os.path.join(base_upload, 'demos', str(lead_id), 'index.html')
    if not os.path.exists(file_path):
        return {"success": False, "error": "HTML demo file does not exist on disk. Please recompile."}

    # Read the local HTML content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        return {"success": False, "error": f"Failed to read index.html: {str(e)}"}

    test_mode = current_app.config.get('TEST_MODE', True)
    
    try:
        if test_mode:
            # Mock Pages publish
            published_url = f"https://flixora.github.io/demo-{lead_id} [TEST_MODE]"
            logger.info(f"[TEST_MODE] Simulating GitHub Pages deploy. URL: {published_url}")
            
            demo.demo_url = published_url
            demo.url_valid = True
            demo.url_reachable = True
            demo.publish_error = ""
            demo.last_validated = datetime.now(timezone.utc)
            
            # Update lead
            lead = Lead.query.get(lead_id)
            if lead:
                lead.last_action = "Demo published to GitHub Pages"
                lead.last_action_at = datetime.now(timezone.utc)
                
            db.session.commit()
            return {"success": True, "published_url": published_url}
            
        else:
            # 1. Resolve GitHub API Credentials
            cred = APICredential.query.filter_by(service_name='github', credential_type='api_key').first()
            github_token = ""
            if cred:
                from app.security.encryption import decrypt_value
                github_token = decrypt_value(cred.encrypted_value)
            else:
                github_token = os.environ.get('GITHUB_TOKEN', '')

            if not github_token:
                err_msg = "GitHub Access Token (PAT) is not configured. Please add it to Settings -> Integrations."
                demo.url_valid = False
                demo.url_reachable = False
                demo.publish_error = err_msg
                db.session.commit()
                return {"success": False, "error": err_msg}

            headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }

            # 2. Authenticate & Get Username
            user_res = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            if user_res.status_code != 200:
                err_msg = f"GitHub authentication failed. Status: {user_res.status_code}, Response: {user_res.text}"
                demo.url_valid = False
                demo.url_reachable = False
                demo.publish_error = err_msg
                db.session.commit()
                return {"success": False, "error": err_msg}

            username = user_res.json().get("login")
            repo_name = f"flixora-demo-{lead_id}"
            
            # 3. Create or verify Repository
            repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
            repo_res = requests.get(repo_url, headers=headers, timeout=10)
            
            if repo_res.status_code == 200:
                logger.info(f"Reusing existing GitHub repository: {repo_name}")
            elif repo_res.status_code == 404:
                logger.info(f"Creating new GitHub repository: {repo_name}")
                create_payload = {
                    "name": repo_name,
                    "description": f"Flixora AI Generated Demo Website for Lead {lead_id}",
                    "private": False,
                    "auto_init": True
                }
                create_res = requests.post("https://api.github.com/user/repos", headers=headers, json=create_payload, timeout=10)
                if create_res.status_code not in [200, 201]:
                    err_msg = f"Failed to create GitHub repository. Status: {create_res.status_code}, Response: {create_res.text}"
                    demo.url_valid = False
                    demo.publish_error = err_msg
                    db.session.commit()
                    return {"success": False, "error": err_msg}
            else:
                err_msg = f"Error checking repository status: {repo_res.status_code}"
                demo.url_valid = False
                demo.publish_error = err_msg
                db.session.commit()
                return {"success": False, "error": err_msg}

            # 4. Commit index.html
            contents_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/index.html"
            file_res = requests.get(contents_url, headers=headers, timeout=10)
            sha = None
            if file_res.status_code == 200:
                sha = file_res.json().get("sha")

            import base64
            encoded_content = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")
            
            commit_payload = {
                "message": "Update Flixora generated demo index.html",
                "content": encoded_content,
                "branch": "main"
            }
            if sha:
                commit_payload["sha"] = sha

            # Try committing on main branch
            commit_res = requests.put(contents_url, headers=headers, json=commit_payload, timeout=10)
            branch_used = "main"
            if commit_res.status_code not in [200, 201]:
                # Try master branch
                commit_payload["branch"] = "master"
                commit_res = requests.put(contents_url, headers=headers, json=commit_payload, timeout=10)
                branch_used = "master"
                if commit_res.status_code not in [200, 201]:
                    err_msg = f"Failed to commit index.html: {commit_res.text}"
                    demo.url_valid = False
                    demo.publish_error = err_msg
                    db.session.commit()
                    return {"success": False, "error": err_msg}

            # 5. Enable/Configure GitHub Pages
            pages_url = f"https://api.github.com/repos/{username}/{repo_name}/pages"
            pages_res = requests.get(pages_url, headers=headers, timeout=10)
            
            if pages_res.status_code != 200:
                enable_payload = {
                    "source": {
                        "branch": branch_used,
                        "path": "/"
                    }
                }
                enable_res = requests.post(pages_url, headers=headers, json=enable_payload, timeout=10)
                if enable_res.status_code not in [200, 201, 204]:
                    err_msg = f"Failed to enable GitHub Pages: {enable_res.text}"
                    demo.url_valid = False
                    demo.publish_error = err_msg
                    db.session.commit()
                    return {"success": False, "error": err_msg}

            # 6. Poll/Verify HTTP Accessibility
            published_url = f"https://{username}.github.io/{repo_name}/"
            logger.info(f"Polling accessibility of published URL: {published_url}")
            
            import time
            reachable = False
            for attempt in range(5):
                try:
                    ping = requests.get(published_url, timeout=5)
                    if ping.status_code == 200:
                        reachable = True
                        break
                except Exception:
                    pass
                time.sleep(2)

            if not reachable:
                # Do not return a fake production URL if unreachable
                err_msg = f"GitHub Pages configured but URL '{published_url}' is not HTTP reachable (DNS/build delay)."
                demo.url_valid = False
                demo.url_reachable = False
                demo.publish_error = err_msg
                db.session.commit()
                return {"success": False, "error": err_msg}

            # Deploy Success
            demo.demo_url = published_url
            demo.url_valid = True
            demo.url_reachable = True
            demo.publish_error = ""
            demo.last_validated = datetime.now(timezone.utc)
            
            lead = Lead.query.get(lead_id)
            if lead:
                lead.last_action = "Demo published to GitHub Pages"
                lead.last_action_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return {"success": True, "published_url": published_url}
            
    except Exception as e:
        logger.error(f"Error publishing demo for lead {lead_id}: {e}")
        demo.url_valid = False
        demo.publish_error = str(e)
        db.session.commit()
        return {"success": False, "error": f"Publishing failed: {str(e)}"}
