"""
Flixora AI Sales Automation Agent — Leads Routes

Drives Lead Discovery configuration form, list query pagination, and detail pages.
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_from_directory
from flask_login import login_required

from app.extensions import db
from app.models import Lead, LeadContact, LeadSource, WebsiteAnalysis, LeadQualification, UploadedFile, PRD
from app.constants import LeadStatus
from app.services.lead_service import run_lead_discovery
from app.security.validation import sanitize_string

leads_bp = Blueprint('leads', __name__, url_prefix='/leads')


@leads_bp.route('')
@login_required
def index():
    """List discovered leads with advanced filtering and pagination."""
    search_query = sanitize_string(request.args.get('search', ''))
    status_filter = sanitize_string(request.args.get('status', ''))
    category_filter = sanitize_string(request.args.get('category', ''))
    rating_filter = request.args.get('min_rating', '')
    
    page = request.args.get('page', 1, type=int)
    
    query = Lead.query

    # Search
    if search_query:
        query = query.filter(
            (Lead.business_name.ilike(f"%{search_query}%")) |
            (Lead.address.ilike(f"%{search_query}%"))
        )

    # Filters
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    if category_filter:
        query = query.filter(Lead.business_category.ilike(f"%{category_filter}%"))
    if rating_filter:
        try:
            query = query.filter(Lead.rating >= float(rating_filter))
        except ValueError:
            pass

    pagination = query.order_by(Lead.lead_score.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    leads = pagination.items
    
    # Categories for filter list
    categories = db.session.query(Lead.business_category).distinct().all()
    categories = [c[0] for c in categories if c[0]]

    return render_template('leads/index.html', 
                           leads=leads, 
                           pagination=pagination, 
                           categories=categories,
                           statuses=LeadStatus.ALL)


@leads_bp.route('/discover', methods=['GET', 'POST'])
@login_required
def discover():
    """Configure search values and launch local business discovery."""
    if request.method == 'POST':
        location = sanitize_string(request.form.get('location', ''))
        category = sanitize_string(request.form.get('category', ''))
        target = int(request.form.get('target', 20))
        min_rating = request.form.get('min_rating', '')
        require_website = request.form.get('require_website') == 'on'

        if not location or not category:
            flash("Please enter both location and category.", "error")
            return render_template('leads/discover.html')

        try:
            res = run_lead_discovery(
                location=location,
                category=category,
                daily_target=target,
                min_rating=min_rating if min_rating else None,
                require_website=require_website
            )

            if res.get("success"):
                flash(f"Discovery completed. Saved {res['saved_count']} new leads. (Skipped {res['duplicate_count']} duplicates).", "success")
                return redirect(url_for('leads.index'))
            else:
                flash(res.get("error", "Failed to run lead discovery."), "error")
        except Exception as e:
            flash(f"Error executing lead discovery: {e}", "error")

    return render_template('leads/discover.html')


@leads_bp.route('/<int:id>')
@login_required
def detail(id):
    """Render details for a specific lead."""
    lead = Lead.query.get_or_404(id)
    phone_contact = LeadContact.query.filter_by(lead_id=id, contact_type='phone').first()
    email_contact = LeadContact.query.filter_by(lead_id=id, contact_type='email').first()
    owner_contact = LeadContact.query.filter_by(lead_id=id, contact_type='owner_name').first()
    
    # Query for booking link if present
    booking_contact = LeadContact.query.filter_by(lead_id=id, contact_type='booking_url').first()
    
    source = LeadSource.query.filter_by(lead_id=id).first()
    analysis = WebsiteAnalysis.query.filter_by(lead_id=id).first()
    qualification = LeadQualification.query.filter_by(lead_id=id).first()
    prd = PRD.query.filter_by(lead_id=id).first()
    
    # Fetch dossier
    dossier = UploadedFile.query.filter_by(lead_id=id).filter(UploadedFile.original_filename.like('LEAD-%.txt')).first()
    
    # Fetch demo project if exists
    from app.models.demo import DemoProject
    demo = DemoProject.query.filter_by(lead_id=id).first()

    return render_template('leads/detail.html', 
                           lead=lead, 
                           phone_contact=phone_contact, 
                           email_contact=email_contact,
                           owner_contact=owner_contact,
                           booking_contact=booking_contact,
                           source=source, 
                           analysis=analysis, 
                           qualification=qualification,
                           prd=prd,
                           dossier=dossier,
                           demo=demo)


@leads_bp.route('/<int:id>/download-dossier')
@login_required
def download_dossier(id):
    """Download the generated lead dossier TXT file."""
    lead = Lead.query.get_or_404(id)
    dossier = UploadedFile.query.filter_by(lead_id=id).filter(UploadedFile.original_filename.like('LEAD-%.txt')).first()
    
    if not dossier:
        # Dynamically generate and save if missing
        from app.services.pipeline_service import generate_lead_dossier_text
        from app.services.file_service import save_generated_file
        import re
        dossier_content = generate_lead_dossier_text(lead)
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', lead.business_name.lower())
        filename = f"LEAD-{lead.id:06d}_{clean_name}.txt"
        
        save_res = save_generated_file(
            file_content=dossier_content,
            original_filename=filename,
            file_type='document',
            lead_id=lead.id
        )
        if save_res.get('success'):
            dossier = UploadedFile.query.get(save_res['file_id'])
        else:
            flash(f"Failed to generate dossier file: {save_res.get('error')}", "error")
            return redirect(url_for('leads.detail', id=id))

    import os
    from flask import current_app
    abs_path = os.path.abspath(os.path.join(current_app.root_path, dossier.file_path))
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=dossier.original_filename)


@leads_bp.route('/<int:id>/update-website', methods=['POST'])
@login_required
def update_website(id):
    """Update lead website URL and trigger auto-processing + client auto-reply."""
    lead = Lead.query.get_or_404(id)
    website_url = sanitize_string(request.form.get('website_url', '')).strip()
    
    if not website_url:
        flash("Please enter a valid website URL.", "error")
        return redirect(url_for('leads.detail', id=id))

    try:
        lead.website_url = website_url
        lead.website_exists = True
        db.session.commit()
        
        # Trigger end-to-end pipeline
        from app.services.pipeline_service import process_lead_end_to_end
        res = process_lead_end_to_end(id, force_prd=True)
        if res.get('success'):
            flash(f"Website URL updated. {res.get('message')}", "success")
        else:
            flash(f"Website updated, but auto-processing failed: {res.get('error')}", "warning")
            
    except Exception as e:
        flash(f"Error during auto-processing: {str(e)}", "error")
        
    return redirect(url_for('leads.detail', id=id))


@leads_bp.route('/<int:id>/trigger-pipeline', methods=['POST'])
@login_required
def trigger_pipeline(id):
    """Trigger the manual auto-analysis and PRD generation pipeline."""
    try:
        from app.services.pipeline_service import process_lead_end_to_end
        res = process_lead_end_to_end(id, force_prd=True)
        if res.get('success'):
            flash(res.get('message'), "success")
        else:
            flash(f"Pipeline execution failed: {res.get('error')}", "error")
    except Exception as e:
        flash(f"Error executing pipeline: {str(e)}", "error")
        
    return redirect(url_for('leads.detail', id=id))


@leads_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_lead(id):
    """Delete a lead and all associated records securely with cascade."""
    lead = Lead.query.get_or_404(id)
    name = lead.business_name
    try:
        db.session.delete(lead)
        db.session.commit()
        flash(f"Lead '{name}' and all associated records have been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting lead: {str(e)}", "error")
    return redirect(url_for('leads.index'))


@leads_bp.route('/delete-multiple', methods=['POST'])
@login_required
def delete_multiple():
    """Delete multiple selected leads and all their associated records securely."""
    lead_ids = request.form.getlist('lead_ids[]')
    if not lead_ids:
        lead_ids = request.form.getlist('lead_ids')
        
    if not lead_ids and request.is_json:
        data = request.get_json()
        lead_ids = data.get('lead_ids', [])

    if not lead_ids:
        if request.is_json:
            return jsonify({"success": False, "error": "No leads selected for deletion."}), 400
        flash("No leads selected for deletion.", "error")
        return redirect(url_for('leads.index'))

    deleted_count = 0
    try:
        for lid in lead_ids:
            lead = Lead.query.get(int(lid))
            if lead:
                db.session.delete(lead)
                deleted_count += 1
        db.session.commit()
        
        message = f"Successfully deleted {deleted_count} leads and all their associated records."
        if request.is_json:
            return jsonify({"success": True, "message": message})
        flash(message, "success")
    except Exception as e:
        db.session.rollback()
        message = f"Error deleting leads: {str(e)}"
        if request.is_json:
            return jsonify({"success": False, "error": message}), 500
        flash(message, "error")

    return redirect(url_for('leads.index'))


@leads_bp.route('/<int:id>/save-demo-url', methods=['POST'])
@login_required
def save_demo_url(id):
    """Save manually entered demo URL and verify it via HTTP ping check."""
    lead = Lead.query.get_or_404(id)
    demo_url = request.form.get('demo_url', '').strip()
    
    if not demo_url:
        flash("Demo URL cannot be empty.", "error")
        return redirect(url_for('leads.detail', id=id))
        
    if not (demo_url.startswith('http://') or demo_url.startswith('https://')):
        flash("Invalid Demo URL: Must start with http:// or https://", "error")
        return redirect(url_for('leads.detail', id=id))
        
    # Perform live HTTP ping verify check
    import requests
    url_valid = False
    try:
        response = requests.get(demo_url, timeout=10)
        if response.status_code < 400:
            url_valid = True
    except Exception as ping_err:
        logger.warning(f"Demo URL verify ping failed: {ping_err}")
        
    from app.models import DemoProject
    demo = DemoProject.query.filter_by(lead_id=id).first()
    if not demo:
        demo = DemoProject(
            lead_id=id,
            demo_name=f"{lead.business_name} Demo",
            demo_url=demo_url,
            url_valid=url_valid,
            url_reachable=url_valid
        )
        db.session.add(demo)
    else:
        demo.demo_url = demo_url
        demo.url_valid = url_valid
        demo.url_reachable = url_valid
        
    db.session.commit()
    
    if url_valid:
        flash("Demo URL saved and verified successfully.", "success")
    else:
        flash("Demo URL saved but verify ping check failed (URL is unreachable).", "warning")
        
    return redirect(url_for('leads.detail', id=id))


@leads_bp.route('/<int:id>/download-prd')
@login_required
def download_prd(id):
    """Download specific lead's personalized PRD as Markdown file."""
    lead = Lead.query.get_or_404(id)
    from app.models import PRD
    prd = PRD.query.filter_by(lead_id=id).first()
    if not prd:
        flash("PRD has not been generated for this lead yet.", "error")
        return redirect(url_for('leads.detail', id=id))
        
    # Build markdown content
    lines = []
    lines.append(f"# {prd.title} (v{prd.current_version})")
    lines.append(f"PRD Status: {prd.status.upper()}")
    lines.append("")
    lines.append("## 1. Business Overview")
    lines.append(prd.business_overview or "Not Available")
    lines.append("")
    lines.append("## 2. Business Analysis")
    lines.append(prd.business_analysis or "Not Available")
    lines.append("")
    lines.append("## 3. Website Goal")
    lines.append(prd.website_goal or "Not Available")
    lines.append("")
    lines.append("## 4. Target Audience")
    lines.append(prd.target_audience or "Not Available")
    lines.append("")
    lines.append("## 5. Design Direction")
    lines.append(prd.design_direction or "Not Available")
    lines.append("")
    lines.append("## 6. Site Structure")
    lines.append(prd.site_structure or "Not Available")
    lines.append("")
    lines.append("## 7. Functional Requirements")
    lines.append(prd.functional_requirements or "Not Available")
    lines.append("")
    lines.append("## 8. Content Requirements")
    lines.append(prd.content_requirements or "Not Available")
    lines.append("")
    lines.append("## 9. Call to Action (CTA) Strategy")
    lines.append(prd.cta_strategy or "Not Available")
    lines.append("")
    lines.append("## 10. Technical Requirements")
    lines.append(prd.technical_requirements or "Not Available")
    
    content = "\n".join(lines)
    from flask import Response
    filename = f"LEAD-{lead.id:06d}_{lead.business_name.lower().replace(' ', '_')}_PRD.md"
    return Response(
        content,
        mimetype="text/markdown",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


@leads_bp.route('/<int:id>/download-txt')
@login_required
def download_full_lead_txt_route(id):
    """Download complete lead details as a plain text file."""
    lead = Lead.query.get_or_404(id)
    from app.services.pipeline_service import generate_lead_dossier_text
    content = generate_lead_dossier_text(lead)
    from flask import Response
    filename = f"LEAD-{lead.id:06d}_{lead.business_name.lower().replace(' ', '_')}_FULL_DETAILS.txt"
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


@leads_bp.route('/<int:id>/outreach/start', methods=['POST'])
@login_required
def start_outreach(id):
    """Start outreach campaign for a lead."""
    lead = Lead.query.get_or_404(id)
    from app.models import DemoProject
    demo = DemoProject.query.filter_by(lead_id=id).first()
    if not demo or not demo.demo_url:
        flash("Cannot start outreach: A valid demo URL must be saved and verified first.", "error")
        return redirect(url_for('leads.detail', id=id))
        
    from app.services.outreach_service import create_outreach_campaign, send_outreach_campaign
    res = create_outreach_campaign(id, channel='whatsapp')
    if not res.get('success'):
        flash(f"Failed to prepare outreach message: {res.get('error')}", "error")
        return redirect(url_for('leads.detail', id=id))
        
    campaign_id = res['campaign_id']
    send_res = send_outreach_campaign(campaign_id)
    if send_res.get('success'):
        flash("Outreach campaign started successfully. Message sent via WhatsApp.", "success")
    else:
        flash(f"Failed to send outreach: {send_res.get('error')}", "error")
        
    return redirect(url_for('leads.detail', id=id))


@leads_bp.route('/<int:id>/outreach/pause', methods=['POST'])
@login_required
def pause_outreach(id):
    """Pause outreach campaign for a lead."""
    from app.models import OutreachCampaign
    campaign = OutreachCampaign.query.filter_by(lead_id=id).first()
    if campaign:
        campaign.status = 'paused'
        db.session.commit()
        flash("Outreach campaign paused.", "success")
    else:
        flash("No active campaign found to pause.", "error")
    return redirect(url_for('leads.detail', id=id))


@leads_bp.route('/<int:id>/outreach/stop', methods=['POST'])
@login_required
def stop_outreach(id):
    """Stop outreach campaign for a lead."""
    from app.models import OutreachCampaign
    campaign = OutreachCampaign.query.filter_by(lead_id=id).first()
    if campaign:
        campaign.status = 'stopped'
        db.session.commit()
        flash("Outreach campaign stopped.", "success")
    else:
        flash("No active campaign found to stop.", "error")
    return redirect(url_for('leads.detail', id=id))


@leads_bp.route('/<int:id>/regenerate-analysis', methods=['POST'])
@login_required
def regenerate_analysis(id):
    """Manually regenerate website analysis."""
    from app.services.analysis_service import analyze_lead_website
    res = analyze_lead_website(id)
    if res.get('success'):
        flash("Website analysis regenerated successfully.", "success")
    else:
        flash(f"Failed to regenerate analysis: {res.get('error')}", "error")
    return redirect(url_for('leads.detail', id=id))


@leads_bp.route('/<int:id>/regenerate-prd', methods=['POST'])
@login_required
def regenerate_prd(id):
    """Manually regenerate PRD."""
    from app.services.prd_service import generate_lead_prd
    res = generate_lead_prd(id, force=True)
    if res.get('success'):
        flash("PRD regenerated successfully.", "success")
    else:
        flash(f"Failed to regenerate PRD: {res.get('error')}", "error")
    return redirect(url_for('leads.detail', id=id))

