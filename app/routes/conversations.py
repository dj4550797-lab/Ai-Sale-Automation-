"""
Flixora AI Sales Automation Agent — Client Conversations Routes
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from app.models import Conversation, Lead
from app.services.conversation_service import (
    create_or_get_conversation, add_message, generate_chatbot_reply, toggle_takeover_status
)
from app.security.validation import sanitize_string
from app.extensions import csrf, db

conversations_bp = Blueprint('conversations', __name__, url_prefix='/conversations')


@conversations_bp.route('')
@login_required
def index():
    """Render the split-panel conversation dashboard (§43)."""
    # Load all conversations
    conversations = Conversation.query.order_by(Conversation.updated_at.desc()).all()
    
    # Auto-resolve target active session
    active_conv_id = request.args.get('id', type=int)
    active_conv = None
    messages = []
    
    if active_conv_id:
        active_conv = Conversation.query.get(active_conv_id)
    elif conversations:
        active_conv = conversations[0]
        
    if active_conv:
        messages = active_conv.messages.all()

    # Also list contacted/replied/interested leads who don't have conversations yet
    leads_without_chat = Lead.query.filter(
        Lead.status.in_(['contacted', 'replied', 'interested', 'negotiation'])
    ).all()
    
    # Filter out those that already have conversations
    existing_lead_ids = {c.lead_id for c in conversations}
    leads_to_start = [l for l in leads_without_chat if l.id not in existing_lead_ids]

    return render_template('conversations/index.html',
                           conversations=conversations,
                           active_conv=active_conv,
                           messages=messages,
                           leads_to_start=leads_to_start)


@conversations_bp.route('/start/<int:lead_id>', methods=['POST'])
@login_required
def start_chat(lead_id):
    """API to manually initialize a conversation session for a qualified lead."""
    conv = create_or_get_conversation(lead_id)
    if conv:
        return jsonify({"success": True, "conversation_id": conv.id})
    return jsonify({"success": False, "error": "Could not initialize conversation."}), 400


@conversations_bp.route('/takeover/<int:conversation_id>', methods=['POST'])
@login_required
def takeover(conversation_id):
    """API endpoint to toggle AI active vs human takeover status (§45)."""
    active = request.form.get('active') == '1'
    
    res = toggle_takeover_status(conversation_id, active, current_user.id)
    if res.get('success'):
        return jsonify({
            "success": True,
            "status": res.get("status"),
            "message": "Takeover toggled successfully."
        })
    return jsonify({"success": False, "error": res.get("error")}), 400


@conversations_bp.route('/reply/<int:conversation_id>', methods=['POST'])
@login_required
def reply(conversation_id):
    """API endpoint to post manual admin responses to client threads."""
    content = request.form.get('content', '')
    if not content.strip():
        return jsonify({"success": False, "error": "Message content cannot be empty."}), 400

    msg = add_message(conversation_id, 'admin', content, sender_name=current_user.display_name)
    if msg:
        return jsonify({
            "success": True,
            "message": {
                "id": msg.id,
                "sender_type": msg.sender_type,
                "sender_name": msg.sender_name,
                "content": msg.content,
                "created_at": msg.created_at.strftime('%H:%M')
            }
        })
    return jsonify({"success": False, "error": "Could not save message."}), 500


@conversations_bp.route('/simulate-client/<int:conversation_id>', methods=['POST'])
@login_required
def simulate_client(conversation_id):
    """API endpoint to simulate client messages and capture automated AI responses (§46)."""
    content = sanitize_string(request.form.get('content', ''))
    if not content.strip():
        return jsonify({"success": False, "error": "Message content cannot be empty."}), 400

    # 1. Log client message
    client_msg = add_message(conversation_id, 'client', content)
    if not client_msg:
        return jsonify({"success": False, "error": "Could not log client message."}), 500

    # 2. Trigger automated AI responder (if AI_ACTIVE)
    ai_msg = generate_chatbot_reply(conversation_id, content)
    
    response_data = {
        "success": True,
        "client_message": {
            "id": client_msg.id,
            "sender_type": client_msg.sender_type,
            "content": client_msg.content,
            "created_at": client_msg.created_at.strftime('%H:%M')
        }
    }
    
    if ai_msg:
        response_data["ai_message"] = {
            "id": ai_msg.id,
            "sender_type": ai_msg.sender_type,
            "sender_name": ai_msg.sender_name,
            "content": ai_msg.content,
            "created_at": ai_msg.created_at.strftime('%H:%M')
        }
        
    return jsonify(response_data)


@conversations_bp.route('/webhook', methods=['GET', 'POST'])
@csrf.exempt
def webhook():
    """Real WhatsApp Webhook endpoint for Meta Cloud API integration."""
    from app.integrations.whatsapp_adapter import WhatsAppAdapter
    from app.utils.logger import get_logger
    logger = get_logger('whatsapp_webhook')
    adapter = WhatsAppAdapter()
    
    if request.method == 'GET':
        # Webhook Verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        # Load verify token from setting
        expected_token = adapter.verify_token or 'default-verify-token'
        
        if mode == 'subscribe' and token == expected_token:
            logger.info("WhatsApp webhook verified successfully.")
            return challenge, 200
        else:
            logger.warning("WhatsApp webhook verification failed.")
            return "Forbidden", 403

    # POST - Receive incoming message payload
    try:
        data = request.get_json() or {}
        # Parse payload
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])
        
        if messages:
            msg_obj = messages[0]
            from_phone = msg_obj.get('from', '')
            msg_body = msg_obj.get('text', {}).get('body', '')
            
            if from_phone and msg_body:
                # 1. Resolve lead by phone number
                from app.models import LeadContact, Lead
                clean_phone = from_phone.replace('+', '').replace(' ', '').strip()
                contact = LeadContact.query.filter_by(contact_type='phone').filter(
                    (LeadContact.value == clean_phone) | 
                    (LeadContact.value == f"+{clean_phone}") |
                    (LeadContact.value.like(f"%{clean_phone[-10:]}%"))
                ).first()
                
                if contact:
                    lead = Lead.query.get(contact.lead_id)
                    if lead:
                        # 2. Get/Create isolated conversation session
                        conv = create_or_get_conversation(lead.id, channel='whatsapp')
                        if conv:
                            # 3. Save incoming client message
                            # (This automatically triggers LLM intent detection and sales stage sync)
                            sender_name = value.get('contacts', [{}])[0].get('profile', {}).get('name', 'Client')
                            client_msg = add_message(conv.id, 'client', msg_body, sender_name=sender_name)
                            
                            # 4. Trigger auto response if AI is active
                            from app.constants import ConversationStatus
                            if conv.status == ConversationStatus.AI_ACTIVE:
                                ai_msg = generate_chatbot_reply(conv.id, msg_body)
                                if ai_msg:
                                    adapter.send_text_message(from_phone, ai_msg.content)
                                    
                else:
                    logger.warning(f"Incoming WhatsApp message from unknown phone number: {from_phone}")
                    
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Error handling WhatsApp webhook: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@conversations_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_conversation(id):
    """Delete a conversation record securely."""
    conv = Conversation.query.get_or_404(id)
    business_name = conv.lead.business_name if conv.lead else "Unknown"
    try:
        db.session.delete(conv)
        db.session.commit()
        flash(f"Conversation for '{business_name}' has been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting conversation: {str(e)}", "error")
    return redirect(url_for('conversations.index'))
