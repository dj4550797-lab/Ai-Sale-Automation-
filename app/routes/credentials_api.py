"""
Flixora AI Sales Automation Agent — Credentials API Routes (§97-98)
"""
from datetime import datetime, timezone
import requests
from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.extensions import db
from app.models import APICredential, LLMProvider
from app.security.encryption import decrypt_value, encrypt_value
from app.security.validation import sanitize_string
from app.services.llm_service import test_provider_connection

credentials_api_bp = Blueprint('credentials_api', __name__, url_prefix='')


@credentials_api_bp.route('/api/credentials/<int:id>/test', methods=['POST'])
@login_required
def test_credential(id):
    """Test connection for a specific API credential."""
    cred = APICredential.query.get_or_404(id)
    
    # If credential is linked to an LLM provider, delegate to the provider test
    if cred.provider_id:
        res = test_provider_connection(cred.provider_id)
        return jsonify(res)

    # General connections (like Google Maps, WhatsApp, Instagram, SMTP)
    api_key = decrypt_value(cred.encrypted_value)
    
    if cred.service_name.lower() == 'google_maps':
        # Test Google Maps Text Search API
        url = f"https://places.googleapis.com/v1/places:searchText?key={api_key}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-FieldMask": "places.id"
        }
        payload = {
            "textQuery": "Google"
        }
        try:
            start_time = datetime.now()
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            latency = (datetime.now() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                cred.is_valid = True
                cred.last_tested_at = datetime.now(timezone.utc)
                cred.last_error = ''
                db.session.commit()
                return jsonify({
                    "success": True,
                    "latency_ms": int(latency),
                    "message": "Google Maps Platform connection successful."
                })
            else:
                error_msg = f"API returned {response.status_code}: {response.text}"
                cred.is_valid = False
                cred.last_tested_at = datetime.now(timezone.utc)
                cred.last_error = error_msg
                db.session.commit()
                return jsonify({
                    "success": False,
                    "error": "Authentication failed. Check API key and permissions."
                })
        except Exception as e:
            cred.is_valid = False
            cred.last_tested_at = datetime.now(timezone.utc)
            cred.last_error = str(e)
            db.session.commit()
            return jsonify({
                "success": False,
                "error": str(e)
            })

    elif cred.service_name.lower() == 'whatsapp':
        # Test WhatsApp via Meta Graph API
        phone_id_cred = APICredential.query.filter_by(
            service_name='whatsapp_phone_id', credential_type='config'
        ).first()
        phone_id = decrypt_value(phone_id_cred.encrypted_value) if phone_id_cred else 'me'
        
        url = f"https://graph.facebook.com/v17.0/{phone_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            start_time = datetime.now()
            response = requests.get(url, headers=headers, timeout=10)
            latency = (datetime.now() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                cred.is_valid = True
                cred.last_tested_at = datetime.now(timezone.utc)
                cred.last_error = ''
                db.session.commit()
                return jsonify({
                    "success": True,
                    "latency_ms": int(latency),
                    "message": "WhatsApp Business API connection successful."
                })
            else:
                cred.is_valid = False
                cred.last_tested_at = datetime.now(timezone.utc)
                cred.last_error = f"Graph API returned {response.status_code}"
                db.session.commit()
                return jsonify({
                    "success": False,
                    "error": f"WhatsApp API error {response.status_code}. Check Phone Number ID and Access Token."
                })
        except Exception as e:
            cred.is_valid = False
            cred.last_tested_at = datetime.now(timezone.utc)
            cred.last_error = str(e)
            db.session.commit()
            return jsonify({"success": False, "error": str(e)})

    elif cred.service_name.lower() == 'instagram':
        # Test Instagram via Graph API
        url = f"https://graph.facebook.com/v17.0/me?access_token={api_key}"
        try:
            start_time = datetime.now()
            response = requests.get(url, timeout=10)
            latency = (datetime.now() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                cred.is_valid = True
                cred.last_tested_at = datetime.now(timezone.utc)
                cred.last_error = ''
                db.session.commit()
                return jsonify({
                    "success": True,
                    "latency_ms": int(latency),
                    "message": "Instagram Graph API connection successful."
                })
            else:
                cred.is_valid = False
                cred.last_tested_at = datetime.now(timezone.utc)
                cred.last_error = f"Graph API returned {response.status_code}"
                db.session.commit()
                return jsonify({
                    "success": False,
                    "error": f"Instagram API error {response.status_code}. Check Access Token."
                })
        except Exception as e:
            cred.is_valid = False
            cred.last_tested_at = datetime.now(timezone.utc)
            cred.last_error = str(e)
            db.session.commit()
            return jsonify({"success": False, "error": str(e)})

    elif cred.service_name.lower() == 'email_smtp':
        # Test SMTP connection (EHLO handshake)
        import smtplib
        host_cred = APICredential.query.filter_by(service_name='email_smtp_host', credential_type='config').first()
        port_cred = APICredential.query.filter_by(service_name='email_smtp_port', credential_type='config').first()
        user_cred = APICredential.query.filter_by(service_name='email_smtp_user', credential_type='config').first()
        tls_cred = APICredential.query.filter_by(service_name='email_smtp_tls', credential_type='config').first()

        smtp_host = decrypt_value(host_cred.encrypted_value) if host_cred else 'smtp.gmail.com'
        smtp_port = int(decrypt_value(port_cred.encrypted_value)) if port_cred else 587
        smtp_user = decrypt_value(user_cred.encrypted_value) if user_cred else ''
        use_tls = decrypt_value(tls_cred.encrypted_value) != 'false' if tls_cred else True
        smtp_pass = api_key

        try:
            start_time = datetime.now()
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.quit()
            latency = (datetime.now() - start_time).total_seconds() * 1000

            cred.is_valid = True
            cred.last_tested_at = datetime.now(timezone.utc)
            cred.last_error = ''
            db.session.commit()
            return jsonify({
                "success": True,
                "latency_ms": int(latency),
                "message": f"SMTP connection to {smtp_host}:{smtp_port} successful."
            })
        except Exception as e:
            cred.is_valid = False
            cred.last_tested_at = datetime.now(timezone.utc)
            cred.last_error = str(e)
            db.session.commit()
            return jsonify({
                "success": False,
                "error": f"SMTP error: {str(e)}"
            })

    # Unsupported or placeholder
    return jsonify({
        "success": False,
        "error": f"Testing not supported for service: {cred.service_name}"
    })


@credentials_api_bp.route('/api/credentials', methods=['POST'])
@login_required
def save_credential():
    """Securely encrypt and save/update a credential."""
    service_name = sanitize_string(request.json.get('service_name', ''))
    credential_type = sanitize_string(request.json.get('credential_type', 'api_key'))
    api_key = request.json.get('api_key', '').strip()

    if not service_name or not api_key:
        return jsonify({
            "success": False,
            "error": "Service name and API key are required."
        }), 400

    encrypted = encrypt_value(api_key)
    last_four = api_key[-4:] if len(api_key) >= 4 else api_key

    # Check existing
    cred = APICredential.query.filter_by(
        service_name=service_name.lower(),
        credential_type=credential_type
    ).first()

    if cred:
        cred.encrypted_value = encrypted
        cred.last_four = last_four
        cred.updated_at = datetime.now(timezone.utc)
    else:
        cred = APICredential(
            service_name=service_name.lower(),
            credential_type=credential_type,
            encrypted_value=encrypted,
            last_four=last_four
        )
        db.session.add(cred)

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Key Saved Securely",
        "credential": {
            "id": cred.id,
            "service_name": cred.service_name,
            "display": f"••••••••••••{cred.last_four}"
        }
    })
