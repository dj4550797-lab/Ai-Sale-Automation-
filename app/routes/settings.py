"""
Flixora AI Sales Automation Agent — Settings Routes (§91-97)
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Setting, User
from app.services.auth_service import change_password
from app.security.validation import sanitize_string
from app.utils.helpers import mask_secret

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('')
@login_required
def index():
    """Settings overview page."""
    return render_template('settings/index.html')


@settings_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Profile settings (§92)."""
    if request.method == 'POST':
        current_user.display_name = sanitize_string(request.form.get('display_name', ''))
        current_user.timezone = sanitize_string(request.form.get('timezone', 'UTC'))
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('settings.profile'))

    return render_template('settings/profile.html')


@settings_bp.route('/profile/password', methods=['POST'])
@login_required
def change_password_route():
    """Change password (§92)."""
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')

    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('settings.profile'))

    if len(new_pw) < 8:
        flash('Password must be at least 8 characters.', 'error')
        return redirect(url_for('settings.profile'))

    try:
        change_password(current_user, current_pw, new_pw)
        flash('Password changed successfully.', 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('settings.profile'))


@settings_bp.route('/company', methods=['GET', 'POST'])
@login_required
def company():
    """Company settings (§93)."""
    if request.method == 'POST':
        fields = ['company_name', 'company_description', 'website', 
                  'business_email', 'business_phone', 'business_location']
        for field in fields:
            value = sanitize_string(request.form.get(field, ''), max_length=1000)
            _set_setting('company', field, value)
        db.session.commit()
        flash('Company settings updated.', 'success')
        return redirect(url_for('settings.company'))

    settings = _get_settings('company')
    return render_template('settings/company.html', settings=settings)


@settings_bp.route('/agent', methods=['GET', 'POST'])
@login_required
def agent():
    """Agent settings (§94)."""
    if request.method == 'POST':
        fields = ['agent_name', 'agent_role', 'communication_tone',
                  'allowed_information', 'restricted_information', 'sales_style']
        for field in fields:
            value = sanitize_string(request.form.get(field, ''), max_length=2000)
            _set_setting('agent', field, value)
        db.session.commit()
        flash('Agent settings updated.', 'success')
        return redirect(url_for('settings.agent'))

    settings = _get_settings('agent')
    return render_template('settings/agent.html', settings=settings)


@settings_bp.route('/integrations')
@login_required
def integrations():
    """API & Integrations settings (§97)."""
    from app.models import LLMProvider, APICredential
    providers = LLMProvider.query.order_by(LLMProvider.priority).all()
    credentials = APICredential.query.all()

    # Mask credentials for display
    masked_creds = []
    for cred in credentials:
        masked_creds.append({
            'id': cred.id,
            'service_name': cred.service_name,
            'credential_type': cred.credential_type,
            'last_four': cred.last_four,
            'display': f'••••••••••••{cred.last_four}' if cred.last_four else '••••••••',
            'is_valid': cred.is_valid,
            'last_tested_at': cred.last_tested_at,
        })

    # Build dynamic integration status map
    service_names = {c.service_name.lower() for c in credentials}
    integrations_status = {
        'google_maps': _get_integration_info(credentials, 'google_maps'),
        'whatsapp': _get_integration_info(credentials, 'whatsapp'),
        'instagram': _get_integration_info(credentials, 'instagram'),
        'email_smtp': _get_integration_info(credentials, 'email_smtp'),
    }

    return render_template('settings/integrations.html',
                          providers=providers, credentials=masked_creds,
                          integrations_status=integrations_status)


def _get_integration_info(credentials, service_name):
    """Get integration status info for a service."""
    for cred in credentials:
        if cred.service_name.lower() == service_name:
            return {
                'configured': True,
                'id': cred.id,
                'display': f'••••••••••••{cred.last_four}' if cred.last_four else '••••••••',
                'is_valid': cred.is_valid,
                'last_tested_at': cred.last_tested_at,
            }
    return {'configured': False}


# ── Helpers ────────────────────────────────────────────────────

def _get_settings(category):
    """Get all settings for a category as a dict."""
    rows = Setting.query.filter_by(category=category).all()
    return {row.key: row.value for row in rows}


def _set_setting(category, key, value, value_type='string'):
    """Set a setting value, creating if needed."""
    setting = Setting.query.filter_by(category=category, key=key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(category=category, key=key, value=value, value_type=value_type)
        db.session.add(setting)
