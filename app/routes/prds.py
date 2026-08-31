"""
Flixora AI Sales Automation Agent — PRD Management Routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone

from app.extensions import db
from app.models import Lead, PRD, PRDVersion, User
from app.constants import PRDStatus
from app.services.prd_service import generate_lead_prd, revise_prd_with_ai
from app.security.validation import sanitize_string

prds_bp = Blueprint('prds', __name__, url_prefix='/prds')


@prds_bp.route('')
@login_required
def index():
    """List generated PRDs."""
    page = request.args.get('page', 1, type=int)
    search_query = sanitize_string(request.args.get('search', ''))
    
    query = PRD.query.join(Lead)
    
    if search_query:
        query = query.filter(
            (Lead.business_name.ilike(f"%{search_query}%")) |
            (PRD.title.ilike(f"%{search_query}%"))
        )
        
    pagination = query.order_by(PRD.updated_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    prds = pagination.items
    return render_template('prds/index.html', 
                           prds=prds, 
                           pagination=pagination)


@prds_bp.route('/<int:id>')
@login_required
def detail(id):
    """View details of a specific PRD with history and revision drawer."""
    prd = PRD.query.get_or_404(id)
    lead = Lead.query.get(prd.lead_id)
    
    # Selected version (defaults to current version)
    version_num = request.args.get('version', prd.current_version, type=int)
    
    version_snapshot = PRDVersion.query.filter_by(prd_id=prd.id, version=version_num).first()
    content = version_snapshot.content_snapshot if version_snapshot else {}
    
    # All versions for selection dropdown
    versions = PRDVersion.query.filter_by(prd_id=prd.id).order_by(PRDVersion.version.desc()).all()
    
    # Compare with another version if requested
    compare_num = request.args.get('compare', type=int)
    compare_content = {}
    if compare_num:
        compare_snap = PRDVersion.query.filter_by(prd_id=prd.id, version=compare_num).first()
        if compare_snap:
            compare_content = compare_snap.content_snapshot

    return render_template('prds/detail.html', 
                           prd=prd, 
                           lead=lead, 
                           content=content, 
                           versions=versions,
                           selected_version=version_num,
                           compare_version=compare_num,
                           compare_content=compare_content)


@prds_bp.route('/run/<int:lead_id>', methods=['POST'])
@login_required
def run(lead_id):
    """Trigger/regenerate PRD for a lead."""
    try:
        res = generate_lead_prd(lead_id)
        if res.get('success'):
            return jsonify({
                "success": True,
                "prd_id": res.get("prd_id"),
                "message": f"PRD generated successfully (Version {res.get('version')})."
            })
        else:
            # Handle case where existing site is adequate
            if res.get('code') == 'adequate_website':
                return jsonify({
                    "success": False,
                    "code": "adequate_website",
                    "error": res.get("error")
                }), 200
            return jsonify({
                "success": False,
                "error": res.get("error", "Generation failed.")
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@prds_bp.route('/<int:id>/action', methods=['POST'])
@login_required
def action(id):
    """Handle approval/rejection status shifts."""
    prd = PRD.query.get_or_404(id)
    action_type = sanitize_string(request.form.get('action', ''))
    
    if action_type == 'approve':
        prd.status = PRDStatus.APPROVED
        prd.approved_at = datetime.now(timezone.utc)
        prd.approved_by = current_user.id
        db.session.commit()
        flash("PRD approved successfully!", "success")
    elif action_type == 'reject':
        prd.status = PRDStatus.REJECTED
        db.session.commit()
        flash("PRD marked as rejected.", "info")
    else:
        flash("Invalid action requested.", "error")
        
    return redirect(url_for('prds.detail', id=prd.id))


@prds_bp.route('/<int:id>/chat', methods=['POST'])
@login_required
def chat(id):
    """Admin AI Chat endpoint to modify PRD content block copy."""
    instruction = sanitize_string(request.form.get('instruction', ''))
    if not instruction:
        return jsonify({"success": False, "error": "Please enter revision instructions."}), 400
        
    try:
        res = revise_prd_with_ai(id, instruction, user_id=current_user.id)
        if res.get('success'):
            return jsonify({
                "success": True,
                "version": res.get("version"),
                "message": "PRD revised successfully."
            })
        else:
            return jsonify({
                "success": False,
                "error": res.get("error", "Revision failed.")
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@prds_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_prd(id):
    """Delete a PRD securely."""
    prd = PRD.query.get_or_404(id)
    title = prd.title
    try:
        db.session.delete(prd)
        db.session.commit()
        flash(f"PRD '{title}' and its version history have been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting PRD: {str(e)}", "error")
    return redirect(url_for('prds.index'))
