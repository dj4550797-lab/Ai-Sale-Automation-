"""
Flixora AI Sales Automation Agent — Demo Website Routes
"""
import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_from_directory, current_app
from flask_login import login_required

from app.extensions import db
from app.models import Lead, PRD, DemoProject
from app.constants import PRDStatus
from app.services.demo_service import compile_demo_html, publish_demo_project
from app.security.validation import sanitize_string

demos_bp = Blueprint('demos', __name__, url_prefix='/demos')


@demos_bp.route('')
@login_required
def index():
    """List prospects and their corresponding demo website mapping states."""
    search_query = sanitize_string(request.args.get('search', ''))
    
    # Query leads with PRDs and Demos joined
    query = Lead.query
    if search_query:
        query = query.filter(Lead.business_name.ilike(f"%{search_query}%"))
        
    leads = query.order_by(Lead.business_name.asc()).all()
    
    # Separate details map
    lead_states = []
    for lead in leads:
        prd = PRD.query.filter_by(lead_id=lead.id).first()
        demo = DemoProject.query.filter_by(lead_id=lead.id).first()
        
        lead_states.append({
            "lead": lead,
            "prd": prd,
            "demo": demo
        })

    return render_template('demos/index.html',
                           lead_states=lead_states)


@demos_bp.route('/generate/<int:lead_id>', methods=['POST'])
@login_required
def generate(lead_id):
    """API endpoint to generate the single-page HTML demo."""
    try:
        res = compile_demo_html(lead_id)
        if res.get('success'):
            return jsonify({
                "success": True,
                "demo_id": res.get("demo_id"),
                "preview_url": res.get("preview_url"),
                "message": "Demo website compiled successfully."
            })
        else:
            return jsonify({
                "success": False,
                "error": res.get("error", "Compilation failed.")
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@demos_bp.route('/publish/<int:lead_id>', methods=['POST'])
@login_required
def publish(lead_id):
    """API endpoint to deploy the demo website statically."""
    try:
        res = publish_demo_project(lead_id)
        if res.get('success'):
            return jsonify({
                "success": True,
                "published_url": res.get("published_url"),
                "message": "Demo published successfully."
            })
        else:
            return jsonify({
                "success": False,
                "error": res.get("error", "Publishing failed.")
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@demos_bp.route('/preview/<int:lead_id>')
@login_required
def preview(lead_id):
    """Render the generated index.html statically for local previewing."""
    base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    demo_dir = os.path.join(base_upload, 'demos', str(lead_id))
    
    if not os.path.exists(os.path.join(demo_dir, 'index.html')):
        flash("No generated index.html found. Please compile the website first.", "error")
        return redirect(url_for('demos.index'))
        
    return send_from_directory(demo_dir, 'index.html')


@demos_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_demo(id):
    """Delete a demo project record securely."""
    demo = DemoProject.query.get_or_404(id)
    lead_id = demo.lead_id
    business_name = demo.lead.business_name if demo.lead else "Unknown"
    try:
        # Safely remove locally stored compiled index.html file if it exists
        base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        demo_dir = os.path.join(base_upload, 'demos', str(lead_id))
        index_file = os.path.join(demo_dir, 'index.html')
        if os.path.exists(index_file):
            try:
                os.remove(index_file)
            except Exception as file_err:
                current_app.logger.warning(f"Failed to delete local demo file: {file_err}")
        
        db.session.delete(demo)
        db.session.commit()
        flash(f"Demo project record for '{business_name}' has been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting demo project: {str(e)}", "error")
    return redirect(url_for('demos.index'))
