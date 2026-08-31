"""
Flixora AI Sales Automation Agent — Sales Pipeline Routes
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required

from app.extensions import db
from app.models import SalesDeal
from app.constants import PipelineStage
from app.services.sales_service import get_deals_by_stage, update_deal_stage
from app.security.validation import sanitize_string

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')


@sales_bp.route('')
@login_required
def index():
    """Render the Sales Kanban Pipeline board page (§52)."""
    stages_map = get_deals_by_stage()
    stages = PipelineStage.ALL
    return render_template('sales/index.html',
                           stages_map=stages_map,
                           stages=stages)


@sales_bp.route('/transition/<int:deal_id>', methods=['POST'])
@login_required
def transition(deal_id):
    """API endpoint to update deal stages and valuations (§52)."""
    to_stage = sanitize_string(request.form.get('stage', ''))
    deal_value = request.form.get('deal_value')
    lost_reason = sanitize_string(request.form.get('lost_reason', ''))
    
    # Optional value parse
    deal_val_float = float(deal_value) if deal_value else None

    res = update_deal_stage(deal_id, to_stage, deal_val_float, lost_reason)
    if res.get('success'):
        return jsonify({
            "success": True,
            "deal_id": res.get("deal_id"),
            "stage": res.get("stage"),
            "message": f"Deal transitioned to stage {to_stage} successfully."
        })
    else:
        return jsonify({"success": False, "error": res.get("error")}), 400


@sales_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_deal(id):
    """Delete a sales deal record securely."""
    deal = SalesDeal.query.get_or_404(id)
    business_name = deal.lead.business_name if deal.lead else "Unknown"
    try:
        db.session.delete(deal)
        db.session.commit()
        flash(f"Sales deal for '{business_name}' has been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting sales deal: {str(e)}", "error")
    return redirect(url_for('sales.index'))
