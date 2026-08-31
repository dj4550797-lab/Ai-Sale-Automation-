"""
Flixora AI Sales Automation Agent — LLM Model Management Routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required

from app.extensions import db
from app.models import LLMProvider, LLMModel
from app.security.validation import sanitize_string

models_bp = Blueprint('models', __name__, url_prefix='/settings/llm')


@models_bp.route('/providers/<int:provider_id>/models')
@login_required
def index(provider_id):
    """List all models for a provider."""
    provider = LLMProvider.query.get_or_404(provider_id)
    models = LLMModel.query.filter_by(provider_id=provider_id).order_by(LLMModel.priority).all()
    return render_template('settings/models.html', provider=provider, models=models)


@models_bp.route('/providers/<int:provider_id>/models/add', methods=['POST'])
@login_required
def add_model(provider_id):
    """Add a model configuration to a provider."""
    provider = LLMProvider.query.get_or_404(provider_id)
    
    model_id = sanitize_string(request.form.get('model_id', ''))
    display_name = sanitize_string(request.form.get('display_name', ''))
    priority = int(request.form.get('priority', 10))

    # Capabilities
    supports_text = request.form.get('supports_text') == 'on'
    supports_vision = request.form.get('supports_vision') == 'on'
    supports_tool_calling = request.form.get('supports_tool_calling') == 'on'
    supports_structured_output = request.form.get('supports_structured_output') == 'on'

    if not model_id:
        flash('Model ID is required.', 'error')
        return redirect(url_for('models.index', provider_id=provider_id))

    model = LLMModel(
        provider_id=provider_id,
        model_id=model_id,
        display_name=display_name or model_id,
        priority=priority,
        supports_text=supports_text,
        supports_vision=supports_vision,
        supports_tool_calling=supports_tool_calling,
        supports_structured_output=supports_structured_output,
        is_enabled=True
    )
    db.session.add(model)
    db.session.commit()

    flash(f"Model '{model.display_name}' added to {provider.name}.", 'success')
    return redirect(url_for('models.index', provider_id=provider_id))


@models_bp.route('/providers/<int:provider_id>/models/<int:id>/edit', methods=['POST'])
@login_required
def edit_model(provider_id, id):
    """Edit a model configuration."""
    model = LLMModel.query.get_or_404(id)
    model.display_name = sanitize_string(request.form.get('display_name', model.display_name))
    model.priority = int(request.form.get('priority', model.priority))
    
    # Capabilities
    model.supports_text = request.form.get('supports_text') == 'on'
    model.supports_vision = request.form.get('supports_vision') == 'on'
    model.supports_tool_calling = request.form.get('supports_tool_calling') == 'on'
    model.supports_structured_output = request.form.get('supports_structured_output') == 'on'

    db.session.commit()
    flash(f"Model '{model.display_name}' updated.", 'success')
    return redirect(url_for('models.index', provider_id=provider_id))


@models_bp.route('/providers/<int:provider_id>/models/<int:id>/delete', methods=['POST'])
@login_required
def delete_model(provider_id, id):
    """Delete a model configuration."""
    model = LLMModel.query.get_or_404(id)
    name = model.display_name
    db.session.delete(model)
    db.session.commit()
    
    flash(f"Model '{name}' deleted.", 'success')
    return redirect(url_for('models.index', provider_id=provider_id))


@models_bp.route('/providers/<int:provider_id>/models/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_model(provider_id, id):
    """Toggle model enabled state."""
    model = LLMModel.query.get_or_404(id)
    model.is_enabled = not model.is_enabled
    db.session.commit()
    
    status_str = 'enabled' if model.is_enabled else 'disabled'
    return jsonify({
        'success': True,
        'message': f"Model '{model.display_name}' is now {status_str}.",
        'is_enabled': model.is_enabled
    })
