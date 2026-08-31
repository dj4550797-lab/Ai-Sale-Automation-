"""
Flixora AI Sales Automation Agent — Website Analysis Routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required

from app.extensions import db
from app.models import Lead, WebsiteAnalysis
from app.services.analysis_service import analyze_lead_website
from app.security.validation import sanitize_string

analysis_bp = Blueprint('analysis', __name__, url_prefix='/analysis')


@analysis_bp.route('')
@login_required
def index():
    """List all website analyses."""
    page = request.args.get('page', 1, type=int)
    search_query = sanitize_string(request.args.get('search', ''))
    
    query = WebsiteAnalysis.query.join(Lead)
    
    if search_query:
        query = query.filter(Lead.business_name.ilike(f"%{search_query}%"))
        
    pagination = query.order_by(WebsiteAnalysis.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    analyses = pagination.items
    return render_template('analysis/index.html', 
                           analyses=analyses, 
                           pagination=pagination)


@analysis_bp.route('/<int:id>')
@login_required
def detail(id):
    """View detailed scorecard and findings for a website analysis."""
    analysis = WebsiteAnalysis.query.get_or_404(id)
    lead = Lead.query.get(analysis.lead_id)
    return render_template('analysis/detail.html', 
                           analysis=analysis, 
                           lead=lead)


@analysis_bp.route('/run/<int:lead_id>', methods=['POST'])
@login_required
def run(lead_id):
    """API endpoint to trigger website analysis for a lead."""
    try:
        res = analyze_lead_website(lead_id)
        if res.get('success'):
            return jsonify({
                "success": True, 
                "analysis_id": res.get("analysis_id"),
                "message": res.get("message", "Analysis completed successfully.")
            })
        else:
            return jsonify({
                "success": False, 
                "error": res.get("error", "Analysis failed.")
            }), 400
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500


@analysis_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_analysis(id):
    """Delete a website analysis record securely."""
    analysis = WebsiteAnalysis.query.get_or_404(id)
    business_name = analysis.lead.business_name if analysis.lead else "Unknown"
    try:
        db.session.delete(analysis)
        db.session.commit()
        flash(f"Website analysis for '{business_name}' has been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting website analysis: {str(e)}", "error")
    return redirect(url_for('analysis.index'))
