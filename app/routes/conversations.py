"""
Flixora AI Sales Automation Agent — Client Conversations Routes
"""
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
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
    """API endpoint to post manual admin responses to client threads and send via WhatsApp."""
    content = request.form.get('content', '')
    if not content.strip():
        return jsonify({"success": False, "error": "Message content cannot be empty."}), 400

    msg = add_message(conversation_id, 'admin', content, sender_name=current_user.display_name)
    if not msg:
        return jsonify({"success": False, "error": "Could not save message."}), 500

    # Dispatch via WhatsApp if lead has a phone number
    conv = Conversation.query.get(conversation_id)
    wa_result = None
    if conv and conv.lead:
        phone = conv.lead.primary_phone
        if phone:
            from app.integrations.whatsapp_adapter import WhatsAppAdapter
            from app.utils.logger import get_logger
            logger = get_logger('whatsapp_outreach')
            wa_adapter = WhatsAppAdapter()
            wa_result = wa_adapter.send_text_message(phone, content)
            logger.info(f"Admin WhatsApp dispatch to {phone}: {wa_result}")

    return jsonify({
        "success": True,
        "whatsapp_dispatched": wa_result.get('success') if wa_result else False,
        "whatsapp_notice": wa_result.get('error') or wa_result.get('notice') if wa_result else None,
        "message": {
            "id": msg.id,
            "sender_type": msg.sender_type,
            "sender_name": msg.sender_name,
            "content": msg.content,
            "created_at": msg.created_at.strftime('%H:%M')
        }
    })


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


# Cache of recently processed WhatsApp message IDs to eliminate Meta timeout retries (4-7 duplicate messages)
PROCESSED_WAMIDS = set()


def _async_process_inbound_ai_reply(app, conv_id, to_phone, msg_content):
    """Execute AI response generation and outbound WhatsApp message asynchronously (§44, §46)."""
    with app.app_context():
        from app.utils.logger import get_logger
        thread_logger = get_logger('whatsapp_webhook')
        try:
            from app.services.conversation_service import generate_chatbot_reply
            from app.integrations.whatsapp_adapter import WhatsAppAdapter
            ai_adapter = WhatsAppAdapter()
            ai_msg = generate_chatbot_reply(conv_id, msg_content)
            if ai_msg and ai_msg.content:
                send_res = ai_adapter.send_text_message(to_phone, ai_msg.content)
                thread_logger.info(f"Async AI auto replied back to {to_phone}: {send_res}")
        except Exception as e_reply:
            thread_logger.error(f"Error in async AI auto reply to {to_phone}: {e_reply}")


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
            msg_id = msg_obj.get('id', '')
            
            # 1. Deduplication check: discard Meta webhook retries instantly
            if msg_id:
                if msg_id in PROCESSED_WAMIDS:
                    logger.info(f"Duplicate WhatsApp webhook message {msg_id} discarded.")
                    return jsonify({"status": "duplicate_ignored"}), 200
                PROCESSED_WAMIDS.add(msg_id)
                if len(PROCESSED_WAMIDS) > 2000:
                    PROCESSED_WAMIDS.pop()

            from_phone = msg_obj.get('from', '')
            msg_type = msg_obj.get('type', 'text')
            if msg_type == 'text':
                msg_body = msg_obj.get('text', {}).get('body', '')
            elif msg_type == 'image':
                caption = msg_obj.get('image', {}).get('caption', '')
                msg_body = f"[Image received] {caption}".strip()
            elif msg_type == 'video':
                caption = msg_obj.get('video', {}).get('caption', '')
                msg_body = f"[Video received] {caption}".strip()
            elif msg_type == 'audio':
                msg_body = "[Audio message received]"
            elif msg_type == 'document':
                filename = msg_obj.get('document', {}).get('filename', 'document')
                msg_body = f"[Document received: {filename}]"
            else:
                msg_body = msg_obj.get('text', {}).get('body', '') or f"[{msg_type} received]"
            
            if from_phone and msg_body:
                from app.models import LeadContact, Lead, OutreachCampaign, OutreachEvent
                from app.constants import OutreachStatus, ConversationStatus
                clean_phone = from_phone.replace('+', '').replace(' ', '').strip()
                last_10 = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
                
                # 1. Resolve lead by phone or whatsapp contact
                contact = LeadContact.query.filter(
                    LeadContact.contact_type.in_(['phone', 'whatsapp'])
                ).filter(
                    (LeadContact.value == clean_phone) | 
                    (LeadContact.value == f"+{clean_phone}") |
                    (LeadContact.value.like(f"%{last_10}%"))
                ).first()
                
                sender_name = value.get('contacts', [{}])[0].get('profile', {}).get('name', '')
                
                if not contact:
                    # Auto-create inbound lead so prospective client inquiries are never lost
                    lead_name = sender_name or f"Inbound Client ({clean_phone[-4:]})"
                    lead = Lead(
                        business_name=lead_name,
                        business_category='Inbound WhatsApp Lead',
                        status='contacted'
                    )
                    db.session.add(lead)
                    db.session.flush()
                    
                    contact = LeadContact(
                        lead_id=lead.id,
                        contact_type='whatsapp',
                        value=f"+{clean_phone}"
                    )
                    db.session.add(contact)
                    db.session.commit()
                else:
                    lead = Lead.query.get(contact.lead_id)

                if lead:
                    # 2. Get/Create isolated conversation session
                    conv = create_or_get_conversation(lead.id, channel='whatsapp')
                    if conv:
                        # 3. Save incoming client message
                        display_sender = sender_name or lead.business_name or 'Client'
                        client_msg = add_message(conv.id, 'client', msg_body, sender_name=display_sender)
                        
                        # 4. Sync outreach campaign status to REPLIED
                        camp = OutreachCampaign.query.filter_by(lead_id=lead.id, channel='whatsapp').first()
                        if camp:
                            camp.status = OutreachStatus.REPLIED
                            camp.replied_at = datetime.now(timezone.utc)
                            evt = OutreachEvent(campaign_id=camp.id, event_type='replied', details=f"Client WhatsApp message: {msg_body[:100]}")
                            db.session.add(evt)
                            db.session.commit()
                        
                        # 5. Trigger autonomous AI auto-response ASYNCHRONOUSLY in background thread
                        # This guarantees Meta receives HTTP 200 within 50ms and never retries
                        if conv.status == ConversationStatus.AI_ACTIVE:
                            import threading
                            app_obj = current_app._get_current_object()
                            threading.Thread(
                                target=_async_process_inbound_ai_reply,
                                args=(app_obj, conv.id, from_phone, msg_body),
                                daemon=True
                            ).start()

        # Handle Meta delivery status callbacks (sent, delivered, read, failed)
        statuses = value.get('statuses', [])
        if statuses:
            from app.models import OutreachCampaign, OutreachEvent
            from app.constants import OutreachStatus
            for st in statuses:
                wamid = st.get('id', '')
                st_val = st.get('status', '')
                errors = st.get('errors', [])
                logger.info(f"Meta delivery status update: {wamid} => {st_val} (errors: {errors})")
                if wamid:
                    evt = OutreachEvent.query.filter(OutreachEvent.details.like(f"%{wamid}%")).first()
                    if evt:
                        camp = OutreachCampaign.query.get(evt.campaign_id)
                        if camp:
                            if st_val == 'delivered':
                                camp.status = OutreachStatus.DELIVERED
                                camp.delivered_at = datetime.now(timezone.utc)
                            elif st_val == 'failed':
                                camp.status = OutreachStatus.FAILED
                                err_title = errors[0].get('title', 'Delivery rejected by Meta') if errors else 'Delivery rejected'
                                camp.error_message = err_title
                            db.session.commit()

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
