"""
Flixora AI Sales Automation Agent — LLM Provider Management Routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required

from app.extensions import db
from app.models import LLMProvider, APICredential, LLMModel
from app.constants import ProviderStatus, LLMProtocol
from app.security.validation import sanitize_string
from app.services.llm_service import test_provider_connection, save_provider_credential

providers_bp = Blueprint('providers', __name__, url_prefix='/settings/llm')


@providers_bp.route('/providers')
@login_required
def index():
    """List all LLM providers."""
    providers = LLMProvider.query.order_by(LLMProvider.priority).all()
    protocols = LLMProtocol.ALL
    return render_template('settings/providers.html', providers=providers, protocols=protocols)


@providers_bp.route('/providers/add', methods=['POST'])
@login_required
def add_provider():
    """Add a new LLM provider."""
    name = sanitize_string(request.form.get('name', ''))
    protocol = sanitize_string(request.form.get('protocol', LLMProtocol.OPENAI_COMPATIBLE))
    base_url = sanitize_string(request.form.get('base_url', ''))
    priority = int(request.form.get('priority', 10))
    api_key = request.form.get('api_key', '').strip()

    if not name:
        flash('Provider name is required.', 'error')
        return redirect(url_for('providers.index'))

    # Create provider
    provider = LLMProvider(
        name=name,
        protocol=protocol,
        base_url=base_url,
        priority=priority,
        status=ProviderStatus.DISABLED,
        is_enabled=True
    )
    db.session.add(provider)
    db.session.commit()

    # Save credential
    if api_key:
        save_provider_credential(provider.id, api_key)

    flash(f"LLM Provider '{name}' added successfully.", 'success')
    return redirect(url_for('providers.index'))


@providers_bp.route('/providers/<int:id>/edit', methods=['POST'])
@login_required
def edit_provider(id):
    """Edit an existing LLM provider."""
    provider = LLMProvider.query.get_or_404(id)
    provider.name = sanitize_string(request.form.get('name', provider.name))
    provider.protocol = sanitize_string(request.form.get('protocol', provider.protocol))
    provider.base_url = sanitize_string(request.form.get('base_url', provider.base_url))
    provider.priority = int(request.form.get('priority', provider.priority))
    
    api_key = request.form.get('api_key', '').strip()
    if api_key and not api_key.startswith('•'):  # If modified
        save_provider_credential(provider.id, api_key)

    db.session.commit()
    flash(f"LLM Provider '{provider.name}' updated.", 'success')
    return redirect(url_for('providers.index'))


@providers_bp.route('/providers/<int:id>/delete', methods=['POST'])
@login_required
def delete_provider(id):
    """Delete a provider, credentials, and models."""
    provider = LLMProvider.query.get_or_404(id)
    name = provider.name
    
    # Cascade delete (handled by relationship cascade in model)
    db.session.delete(provider)
    db.session.commit()

    flash(f"LLM Provider '{name}' deleted.", 'success')
    return redirect(url_for('providers.index'))


@providers_bp.route('/providers/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_provider(id):
    """Toggle provider enabled state."""
    provider = LLMProvider.query.get_or_404(id)
    provider.is_enabled = not provider.is_enabled
    provider.status = ProviderStatus.HEALTHY if provider.is_enabled else ProviderStatus.DISABLED
    db.session.commit()
    
    status_str = 'enabled' if provider.is_enabled else 'disabled'
    return jsonify({
        'success': True,
        'message': f"Provider '{provider.name}' is now {status_str}.",
        'is_enabled': provider.is_enabled
    })


@providers_bp.route('/providers/<int:id>/test', methods=['POST'])
@login_required
def test_provider(id):
    """Run connection test and return JSON response."""
    res = test_provider_connection(id)
    return jsonify(res)
