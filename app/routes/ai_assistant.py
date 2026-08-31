"""
Flixora AI Sales Automation Agent — Admin AI Assistant Routes
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required

from app.services.assistant_service import answer_admin_query
from app.security.validation import sanitize_string

ai_assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai-assistant')


@ai_assistant_bp.route('')
@login_required
def index():
    """Render the Admin AI Assistant workspace page."""
    return render_template('ai_assistant/index.html')


@ai_assistant_bp.route('/message', methods=['POST'])
@login_required
def message():
    """API endpoint to post chat queries to the AI Assistant."""
    message_content = sanitize_string(request.form.get('message', ''))
    if not message_content:
        return jsonify({"success": False, "error": "Query message cannot be empty."}), 400
        
    try:
        import json
        history_raw = request.form.get('history', '[]')
        try:
            history = json.loads(history_raw)
        except Exception:
            history = None
            
        res = answer_admin_query(message_content, history)
        if res.get('success'):
            return jsonify({
                "success": True,
                "reply": res.get("reply"),
                "tool_called": res.get("tool_called")
            })
        else:
            return jsonify({
                "success": False,
                "error": res.get("error", "Failed to answer query.")
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
