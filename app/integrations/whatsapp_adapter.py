"""
Flixora AI Sales Automation Agent — WhatsApp Cloud API Integration Adapter
"""
import requests
from flask import current_app
from app.models import Setting, APICredential
from app.security.encryption import decrypt_value
from app.utils.logger import get_logger

logger = get_logger('integrations')


class WhatsAppAdapter:
    """Meta WhatsApp Business Cloud API Client Adapter."""

    def __init__(self):
        self.phone_number_id = None
        self.access_token = None
        self.verify_token = None
        self._load_config()

    def _load_config(self):
        """Load and decrypt WhatsApp configuration credentials from DB."""
        try:
            # 1. Access Token
            cred_token = APICredential.query.filter_by(service_name='whatsapp', credential_type='api_key').first()
            if cred_token:
                self.access_token = decrypt_value(cred_token.encrypted_value)
            else:
                setting_token = Setting.query.filter_by(category='messaging', key='whatsapp_access_token').first()
                if setting_token and setting_token.value:
                    try:
                        self.access_token = decrypt_value(setting_token.value)
                    except Exception:
                        self.access_token = setting_token.value

            # 2. Phone Number ID
            cred_phone = APICredential.query.filter_by(service_name='whatsapp_phone_id', credential_type='config').first()
            if cred_phone:
                self.phone_number_id = decrypt_value(cred_phone.encrypted_value)
            else:
                setting_phone = Setting.query.filter_by(category='messaging', key='whatsapp_phone_number_id').first()
                if setting_phone:
                    self.phone_number_id = setting_phone.value

            # 3. Verify Token
            cred_verify = APICredential.query.filter_by(service_name='whatsapp_verify_token', credential_type='config').first()
            if cred_verify:
                self.verify_token = decrypt_value(cred_verify.encrypted_value)
            else:
                setting_verify = Setting.query.filter_by(category='messaging', key='whatsapp_verify_token').first()
                if setting_verify:
                    self.verify_token = setting_verify.value

        except Exception as e:
            logger.error(f"Error loading WhatsApp configurations: {str(e)}")

    def is_configured(self):
        """Check if minimum required credentials exist."""
        self._load_config()
        return bool(self.phone_number_id and self.access_token)

    def test_connection(self):
        """Test sending a template test message to Meta endpoint to verify credentials."""
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp credentials are not configured in settings."}

        url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        # Meta standard test sandbox payload
        payload = {
            "messaging_product": "whatsapp",
            "to": "15555555555",  # Sandbox test number
            "type": "template",
            "template": {
                "name": "hello_world",
                "language": {
                    "code": "en_US"
                }
            }
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                return {"success": True, "message": "Connection tested successfully."}
            else:
                return {"success": False, "error": f"WhatsApp API error: {response.text}"}
        except Exception as e:
            return {"success": False, "error": f"Connection request failed: {str(e)}"}

    def send_text_message(self, recipient_phone, message_text):
        """Send standard WhatsApp text message to target phone number."""
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp API is not configured."}

        url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Clean phone format
        clean_phone = recipient_phone.replace('+', '').replace(' ', '').strip()
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "text",
            "text": {
                "body": message_text
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code in [200, 201]:
                res_data = response.json()
                msg_id = res_data.get('messages', [{}])[0].get('id', '')
                return {"success": True, "message_id": msg_id}
            else:
                logger.error(f"WhatsApp API Send Error: {response.text}")
                return {"success": False, "error": f"WhatsApp API Error {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"WhatsApp API exception: {str(e)}")
            return {"success": False, "error": str(e)}
