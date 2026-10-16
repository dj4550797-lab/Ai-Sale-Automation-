"""
Flixora AI Sales Automation Agent — Leads Routes

Drives Lead Discovery configuration form, list query pagination, and detail pages.
"""
from datetime import datetime, timezone
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
    else:
        query = query.filter(Lead.status != LeadStatus.ARCHIVED)

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
    archived_count = Lead.query.filter_by(status=LeadStatus.ARCHIVED).count()

    return render_template('leads/index.html', 
                           leads=leads, 
                           pagination=pagination, 
                           categories=categories,
                           statuses=LeadStatus.ALL,
                           archived_count=archived_count)


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
    """Delete a single lead — soft archive into Storage or permanent purge."""
    lead = Lead.query.get_or_404(id)
    name = lead.business_name
    is_archive = (request.args.get('archive') == '1' or 
                  request.form.get('archive') in ['1', 'true', 'on'])
    try:
        if is_archive:
            lead.status = LeadStatus.ARCHIVED
            lead.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            flash(f"Lead '{name}' moved to Storage & Recycle Bin. You can recover it anytime from Storage Hub.", "success")
        else:
            from app.services.lead_service import purge_lead_safely
            purge_lead_safely(id)
            db.session.commit()
            flash(f"Lead '{name}' permanently deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting lead: {str(e)}", "error")

    ref = request.referrer
    if ref and ('storage' in ref or 'leads' in ref):
        return redirect(ref)
    return redirect(url_for('leads.index'))


@leads_bp.route('/delete-multiple', methods=['POST'])
@login_required
def delete_multiple():
    """Bulk delete or archive multiple selected leads."""
    lead_ids = request.form.getlist('lead_ids[]')
    if not lead_ids:
        lead_ids = request.form.getlist('lead_ids')
    if not lead_ids and request.is_json:
        data = request.get_json(silent=True) or {}
        lead_ids = data.get('lead_ids', [])

    if not lead_ids:
        if request.is_json:
            return jsonify({"success": False, "error": "No leads selected for deletion."}), 400
        flash("No leads were selected for deletion.", "warning")
        return redirect(request.referrer or url_for('leads.index'))

    is_archive = (request.args.get('archive') == '1' or 
                  request.form.get('archive') in ['1', 'true', 'on'])
    
    count = 0
    try:
        for lid in lead_ids:
            try:
                lead = Lead.query.get(int(lid))
                if lead:
                    if is_archive:
                        lead.status = LeadStatus.ARCHIVED
                        lead.updated_at = datetime.now(timezone.utc)
                    else:
                        from app.services.lead_service import purge_lead_safely
                        purge_lead_safely(int(lid))
                    count += 1
            except (ValueError, TypeError):
                continue
        db.session.commit()
        if is_archive:
            msg = f"Moved {count} leads to Storage & Recycle Bin. You can recover them anytime."
        else:
            msg = f"Permanently purged {count} selected leads."
        
        if request.is_json:
            return jsonify({"success": True, "message": msg})
        flash(msg, "success")
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({"success": False, "error": str(e)}), 500
        flash(f"Error deleting selected leads: {str(e)}", "error")

    return redirect(request.referrer or url_for('leads.index'))


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
    lead.last_action = "Demo URL saved"
    lead.last_action_at = datetime.now(timezone.utc)
    if lead.status == LeadStatus.WAITING_FOR_DEMO:
        lead.status = LeadStatus.QUALIFIED
        
    db.session.commit()
    
    # Auto outreach if requested
    auto_outreach = request.form.get('auto_outreach') == '1'
    media_url = request.form.get('media_url', '').strip() or None
    media_type = request.form.get('media_type', '').strip() or None
    if auto_outreach and url_valid:
        from app.services.outreach_service import create_outreach_campaign, send_outreach_campaign
        camp_res = create_outreach_campaign(id, channel='whatsapp', media_url=media_url, media_type=media_type)
        if camp_res.get('success'):
            send_res = send_outreach_campaign(camp_res['campaign_id'])
            if send_res.get('success'):
                flash("Demo URL saved, verified, and WhatsApp pitch sent automatically!", "success")
                return redirect(url_for('leads.detail', id=id))
            else:
                flash(f"Demo URL verified, but auto-outreach failed: {send_res.get('error')}", "warning")
                return redirect(url_for('leads.detail', id=id))
        else:
            flash(f"Demo URL verified, but pitch preparation failed: {camp_res.get('error')}", "warning")
            return redirect(url_for('leads.detail', id=id))
            
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
    media_url = request.form.get('media_url', '').strip() or None
    media_type = request.form.get('media_type', '').strip() or None
    res = create_outreach_campaign(id, channel='whatsapp', media_url=media_url, media_type=media_type)
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


# ── Storage & Recovery Hub Management Routes ───────────────────────


@leads_bp.route('/<int:id>/restore', methods=['POST'])
@login_required
def restore_lead(id):
    """Restore a single archived lead back to the active pipeline."""
    lead = Lead.query.get_or_404(id)
    try:
        # Determine appropriate status to restore to
        if lead.prds.count() > 0 and lead.demos.count() > 0:
            lead.status = LeadStatus.WAITING_FOR_DEMO
        elif lead.prds.count() > 0:
            lead.status = LeadStatus.QUALIFIED
        else:
            lead.status = LeadStatus.QUALIFIED
        lead.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f"Lead '{lead.business_name}' successfully recovered and restored to active pipeline!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error restoring lead: {str(e)}", "error")
    return redirect(request.referrer or url_for('leads.storage_hub'))


@leads_bp.route('/restore-all', methods=['POST'])
@login_required
def restore_all():
    """Recover all archived leads in 1-click."""
    try:
        archived = Lead.query.filter_by(status=LeadStatus.ARCHIVED).all()
        count = len(archived)
        for lead in archived:
            lead.status = LeadStatus.QUALIFIED
            lead.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f"🎉 Successfully recovered all {count} archived leads back to active pipeline!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error recovering all leads: {str(e)}", "error")
    return redirect(url_for('leads.storage_hub'))


@leads_bp.route('/<int:id>/delete-chat', methods=['POST'])
@login_required
def delete_lead_chat(id):
    """Delete message history and conversation records for a lead."""
    lead = Lead.query.get_or_404(id)
    try:
        from app.models import Conversation, Message
        convs = Conversation.query.filter_by(lead_id=id).all()
        total_msgs = 0
        for c in convs:
            deleted_msgs = Message.query.filter_by(conversation_id=c.id).delete()
            total_msgs += deleted_msgs
            db.session.delete(c)
        db.session.commit()
        flash(f"Cleared {total_msgs} chat messages for '{lead.business_name}'.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error clearing chat history: {str(e)}", "error")
    return redirect(request.referrer or url_for('leads.storage_hub'))


@leads_bp.route('/delete-chats-multiple', methods=['POST'])
@login_required
def delete_chats_multiple():
    """Multi-select delete chat conversations for multiple leads."""
    lead_ids = request.form.getlist('lead_ids[]')
    if not lead_ids:
        flash("No conversations were selected for deletion.", "warning")
        return redirect(request.referrer or url_for('leads.storage_hub'))

    try:
        from app.models import Conversation, Message
        cleared_leads = 0
        cleared_msgs = 0
        for lid in lead_ids:
            try:
                lid_int = int(lid)
                convs = Conversation.query.filter_by(lead_id=lid_int).all()
                if convs:
                    for c in convs:
                        cleared_msgs += Message.query.filter_by(conversation_id=c.id).delete()
                        db.session.delete(c)
                    cleared_leads += 1
            except (ValueError, TypeError):
                continue
        db.session.commit()
        flash(f"Cleared chat histories ({cleared_msgs} messages) across {cleared_leads} leads.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error bulk clearing chats: {str(e)}", "error")
    return redirect(request.referrer or url_for('leads.storage_hub'))


@leads_bp.route('/storage')
@login_required
def storage_hub():
    """Storage, Archive, Chat Purge & Media Hub."""
    from app.models import Conversation, Message, UploadedFile
    
    # 1. Archived Leads (Recycle Bin)
    archived_leads = Lead.query.filter_by(status=LeadStatus.ARCHIVED).order_by(Lead.updated_at.desc()).all()
    
    # 2. Active Leads
    active_leads = Lead.query.filter(Lead.status != LeadStatus.ARCHIVED).order_by(Lead.lead_score.desc()).limit(100).all()
    
    # 3. Leads with Conversation Chats
    leads_with_chats = db.session.query(Lead).join(Conversation).distinct().all()
    chat_dossiers = []
    for l in leads_with_chats:
        c = Conversation.query.filter_by(lead_id=l.id).order_by(Conversation.updated_at.desc()).first()
        msg_count = Message.query.filter_by(conversation_id=c.id).count() if c else 0
        last_msg = Message.query.filter_by(conversation_id=c.id).order_by(Message.created_at.desc()).first() if c else None
        chat_dossiers.append({
            'lead': l,
            'conversation': c,
            'msg_count': msg_count,
            'last_msg': last_msg
        })
    
    # 4. Media Files
    media_files = UploadedFile.query.order_by(UploadedFile.created_at.desc()).all()
    
    return render_template(
        'leads/storage.html',
        archived_leads=archived_leads,
        active_leads=active_leads,
        chat_dossiers=chat_dossiers,
        media_files=media_files
    )


@leads_bp.route('/storage/delete-media', methods=['POST'])
@login_required
def delete_media_multiple():
    """Multi-select bulk delete media files."""
    file_ids = request.form.getlist('file_ids[]')
    if not file_ids:
        flash("No media files selected.", "warning")
        return redirect(url_for('leads.storage_hub'))
    
    try:
        from app.models import UploadedFile
        import os
        from flask import current_app
        deleted_count = 0
        for fid in file_ids:
            try:
                uf = UploadedFile.query.get(int(fid))
                if uf:
                    # Remove from disk if exists
                    if uf.file_path and os.path.exists(uf.file_path):
                        try:
                            os.remove(uf.file_path)
                        except Exception:
                            pass
                    db.session.delete(uf)
                    deleted_count += 1
            except (ValueError, TypeError):
                continue
        db.session.commit()
        flash(f"Successfully deleted {deleted_count} media assets.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting media files: {str(e)}", "error")
    return redirect(url_for('leads.storage_hub'))


