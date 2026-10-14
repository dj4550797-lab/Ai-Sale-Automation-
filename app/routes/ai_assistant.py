"""
Flixora AI Sales Automation Agent — Admin AI Assistant Routes

Features:
- Full conversation persistence with auto-save
- Recent chat sessions history sidebar
- Image upload and multimodal AI vision analysis
- Knowledge Base and CRM database insights
"""
import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.assistant_chat import AssistantSession, AssistantMessage
from app.services.assistant_service import answer_admin_query
from app.security.validation import sanitize_string

ai_assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai-assistant')


@ai_assistant_bp.route('')
@login_required
def index():
    """Render the Admin AI Assistant workspace with recent session threads."""
    user_id = current_user.id if hasattr(current_user, 'id') else None
    
    # Query sessions for current user or all admin sessions
    query = AssistantSession.query
    if user_id:
        query = query.filter((AssistantSession.user_id == user_id) | (AssistantSession.user_id == None))
    sessions = query.order_by(AssistantSession.updated_at.desc()).limit(30).all()

    # Active session parameter or most recent session or None
    active_session_id = request.args.get('session_id', type=int)
    active_session = None
    if active_session_id:
        active_session = AssistantSession.query.get(active_session_id)
    elif sessions:
        active_session = sessions[0]

    messages = []
    if active_session:
        messages = active_session.messages.all()

    from app.models import LLMModel
    models = LLMModel.query.filter_by(is_enabled=True).order_by(LLMModel.priority.desc()).all()

    return render_template(
        'ai_assistant/index.html',
        sessions=sessions,
        active_session=active_session,
        initial_messages=messages,
        models=models
    )


@ai_assistant_bp.route('/session/new', methods=['POST'])
@login_required
def create_session():
    """Create a new chat session."""
    user_id = current_user.id if hasattr(current_user, 'id') else None
    session = AssistantSession(
        title="New Conversation",
        user_id=user_id
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({
        "success": True,
        "session": session.to_dict()
    })


@ai_assistant_bp.route('/session/<int:session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """Retrieve messages for an existing session."""
    session = AssistantSession.query.get_or_404(session_id)
    messages = [m.to_dict() for m in session.messages.all()]
    return jsonify({
        "success": True,
        "session": session.to_dict(),
        "messages": messages
    })


@ai_assistant_bp.route('/session/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    """Delete a chat session and all its messages."""
    session = AssistantSession.query.get_or_404(session_id)
    db.session.delete(session)
    db.session.commit()
    return jsonify({"success": True, "message": "Chat session deleted successfully."})


@ai_assistant_bp.route('/message', methods=['POST'])
@login_required
def message():
    """Post chat queries with auto-save and optional image upload."""
    message_content = sanitize_string(request.form.get('message', ''))
    session_id = request.form.get('session_id', type=int)
    
    # Handle image upload
    image_file = request.files.get('image')
    image_rel_path = None
    image_abs_path = None

    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext in ['png', 'jpg', 'jpeg', 'webp', 'gif']:
            unique_name = f"{uuid.uuid4().hex[:12]}_{filename}"
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'assistant')
            os.makedirs(upload_dir, exist_ok=True)
            image_abs_path = os.path.join(upload_dir, unique_name)
            image_file.save(image_abs_path)
            image_rel_path = f"/files/assistant/{unique_name}"

    if not message_content and not image_rel_path:
        return jsonify({"success": False, "error": "Query message or image cannot be empty."}), 400

    # Retrieve or create session
    user_id = current_user.id if hasattr(current_user, 'id') else None
    session = None
    if session_id:
        session = AssistantSession.query.get(session_id)

    if not session:
        first_title = (message_content[:35] + '...') if len(message_content) > 35 else (message_content or "Image Analysis")
        session = AssistantSession(
            title=first_title,
            user_id=user_id
        )
        db.session.add(session)
        db.session.commit()
    elif session.title == "New Conversation" and message_content:
        session.title = (message_content[:35] + '...') if len(message_content) > 35 else message_content
        db.session.commit()

    # 1. Save User Message (Auto-Save!)
    user_msg = AssistantMessage(
        session_id=session.id,
        sender='user',
        content=message_content or "(Uploaded image for analysis)",
        image_path=image_rel_path
    )
    db.session.add(user_msg)
    session.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    # 2. Build conversation history for LLM context
    history_records = AssistantMessage.query.filter_by(session_id=session.id)\
        .order_by(AssistantMessage.created_at.asc()).all()[-10:]
    history = [{"sender": m.sender, "content": m.content} for m in history_records[:-1]]

    model_name = request.form.get('model', '').strip() or None

    # 3. Call AI Service
    try:
        res = answer_admin_query(message_content, history, image_path=image_abs_path, model_name=model_name)
        reply_text = res.get("reply", "No response generated.")
        tool_called = res.get("tool_called", "none")

        # 4. Save Assistant Message (Auto-Save!)
        assistant_msg = AssistantMessage(
            session_id=session.id,
            sender='assistant',
            content=reply_text,
            tool_called=tool_called
        )
        db.session.add(assistant_msg)
        session.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "success": True,
            "session_id": session.id,
            "session_title": session.title,
            "reply": reply_text,
            "tool_called": tool_called,
            "image_url": image_rel_path,
            "user_message_id": user_msg.id,
            "assistant_message_id": assistant_msg.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Failed to process query: {str(e)}"
        }), 500
