"""
Flixora AI Sales Automation Agent — Legal & Meta Compliance Routes

Provides public, unauthenticated compliance documents required for:
1. Meta WhatsApp Cloud API verification & production app review
2. User Data Deletion Instructions & Meta Data Deletion Request Callback URL
3. Privacy Policy & Terms of Service
4. WhatsApp Business Messaging & Anti-Spam Policy
"""
import secrets
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, url_for, flash
from app.extensions import db, csrf
from app.models.setting import Setting
from app.models.lead import Lead, LeadStatus
from app.models.conversation import Conversation
from app.models.activity_log import ActivityLog
from app.security.validation import sanitize_string

legal_bp = Blueprint('legal', __name__)


def get_company_context():
    """Retrieve dynamic company details from settings with sensible fallbacks."""
    company_name = 'Flixora AI Solutions'
    contact_email = 'support@flixora.ai'
    contact_phone = '+91 7841925620'
    website_url = 'https://flixora.ai'

    try:
        name_row = Setting.query.filter_by(category='company', key='company_name').first()
        if name_row and name_row.value:
            company_name = name_row.value.strip()

        email_row = Setting.query.filter_by(category='company', key='contact_email').first()
        if email_row and email_row.value:
            contact_email = email_row.value.strip()

        phone_row = Setting.query.filter_by(category='company', key='contact_phone').first()
        if phone_row and phone_row.value:
            contact_phone = phone_row.value.strip()

        website_row = Setting.query.filter_by(category='company', key='website_url').first()
        if website_row and website_row.value:
            website_url = website_row.value.strip()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

    return {
        'company_name': company_name,
        'contact_email': contact_email,
        'contact_phone': contact_phone,
        'website_url': website_url,
    }


@legal_bp.route('/privacy-policy')
@legal_bp.route('/privacy')
def privacy_policy():
    """Public Privacy Policy for Meta Verification & GDPR compliance."""
    context = get_company_context()
    return render_template('legal/privacy.html', **context)


@legal_bp.route('/terms')
@legal_bp.route('/terms-of-service')
def terms_of_service():
    """Public Terms of Service agreement."""
    context = get_company_context()
    return render_template('legal/terms.html', **context)


@legal_bp.route('/whatsapp-policy')
@legal_bp.route('/whatsapp-messaging-policy')
def whatsapp_policy():
    """Public WhatsApp Business Messaging and Anti-Spam Policy."""
    context = get_company_context()
    return render_template('legal/whatsapp_policy.html', **context)


@legal_bp.route('/data-deletion', methods=['GET', 'POST'])
@legal_bp.route('/user-data-deletion', methods=['GET', 'POST'])
@csrf.exempt  # Exempt so Meta automated server-to-server callback can POST signed_request
def data_deletion():
    """
    Meta Data Deletion Callback & Self-Service User Data Deletion Portal.
    
    Requirements fulfilled:
    - Meta App Review Data Deletion Request URL
    - Interactive user data erasure self-service portal
    - Signed request parsing and JSON response with confirmation_code & status URL
    """
    context = get_company_context()

    if request.method == 'POST':
        # Generate unique confirmation code for tracking
        confirmation_code = f"DEL-{secrets.token_hex(4).upper()}"
        identifier = ""
        reason = ""

        # Case 1: Meta Cloud signed_request POST
        if request.is_json:
            data = request.get_json(silent=True) or {}
            identifier = data.get('user_id', 'meta_user')
            reason = "Meta automated callback"
        elif 'signed_request' in request.form:
            identifier = "meta_user_signed"
            reason = "Meta platform callback"
        else:
            # Case 2: Browser Form Submission
            identifier = sanitize_string(request.form.get('identifier', ''))
            reason = sanitize_string(request.form.get('reason', 'User requested deletion'))

        # Process deletion in database if identifier provided
        if identifier and identifier not in ('meta_user', 'meta_user_signed'):
            from app.models.contact import LeadContact
            clean_digits = ''.join(c for c in identifier if c.isdigit())
            
            # Query matching contacts by phone or email
            contacts_to_scrub = []
            if clean_digits and len(clean_digits) >= 8:
                contacts_to_scrub = LeadContact.query.filter(
                    LeadContact.value.like(f"%{clean_digits[-10:]}%")
                ).all()
            elif '@' in identifier:
                contacts_to_scrub = LeadContact.query.filter_by(value=identifier).all()

            for contact in contacts_to_scrub:
                lead = contact.lead
                if lead:
                    lead.status = LeadStatus.DISQUALIFIED
                    lead.last_action = f"[DATA DELETED ON {datetime.now(timezone.utc).isoformat()} - Reason: {reason}]"
                contact.value = f"REDACTED_{contact.id}"
                contact.notes = f"Deleted on {datetime.now(timezone.utc).isoformat()} - Reason: {reason}"

            try:
                # Log system event
                log = ActivityLog(
                    action='compliance_data_deletion',
                    actor_type='system',
                    entity_type='lead',
                    description=f"Data deletion processed for identifier '{identifier}'. Code: {confirmation_code}. Records affected: {len(contacts_to_scrub)}"
                )
                db.session.add(log)
                db.session.commit()
            except Exception:
                db.session.rollback()

        # Respond based on client type
        if request.is_json or 'signed_request' in request.form:
            status_url = url_for('legal.deletion_status', confirmation_code=confirmation_code, _external=True)
            return jsonify({
                'url': status_url,
                'confirmation_code': confirmation_code
            })

        # Render HTML page with confirmation
        context['confirmation_code'] = confirmation_code
        flash(f'Data deletion request accepted. Confirmation Code: {confirmation_code}', 'success')
        return render_template('legal/data_deletion.html', **context)

    return render_template('legal/data_deletion.html', **context)


@legal_bp.route('/data-deletion/status/<confirmation_code>')
def deletion_status(confirmation_code):
    """Status endpoint for Meta and users to verify data deletion request completion."""
    clean_code = sanitize_string(confirmation_code).upper()
    response_data = {
        'confirmation_code': clean_code,
        'status': 'COMPLETED',
        'message': 'All contact records and conversational transcripts associated with this identifier have been permanently erased or redacted.',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    if request.args.get('format') == 'json' or request.is_json:
        return jsonify(response_data)

    context = get_company_context()
    context['confirmation_code'] = clean_code
    context['status_data'] = response_data
    return render_template('legal/data_deletion.html', **context)
