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


@models_bp.route('/providers/<int:provider_id>/models/discover')
@login_required
def discover_models(provider_id):
    """AI Auto-Discover available Free, Pro, and Best models for this provider."""
    provider = LLMProvider.query.get_or_404(provider_id)
    p_name = (provider.name or '').lower()

    # Pre-curated verified catalog by provider type
    catalog = {
        'free': [
            {
                'model_id': 'meta-llama/llama-3.3-70b-instruct:free',
                'display_name': 'Llama 3.3 70B (Free Tier)',
                'tier': 'free',
                'context': '128k',
                'speed': 'Fast',
                'priority': 5,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Meta latest flagship open model, 100% free on OpenRouter, strong reasoning & tool use.'
            },
            {
                'model_id': 'deepseek/deepseek-r1:free',
                'display_name': 'DeepSeek R1 Reasoning (Free)',
                'tier': 'free',
                'context': '64k',
                'speed': 'Moderate',
                'priority': 6,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': False,
                'supports_structured_output': True,
                'desc': 'State-of-the-art open reasoning model rivaling OpenAI o1, completely free tier.'
            },
            {
                'model_id': 'google/gemini-2.0-flash-exp:free',
                'display_name': 'Gemini 2.0 Flash Exp (Free)',
                'tier': 'free',
                'context': '1M',
                'speed': 'Ultra Fast',
                'priority': 4,
                'supports_text': True,
                'supports_vision': True,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Google next-gen multimodal speed demon with 1 Million token context and vision, free.'
            },
            {
                'model_id': 'google/gemini-2.0-flash-thinking-exp:free',
                'display_name': 'Gemini 2.0 Flash Thinking (Free)',
                'tier': 'free',
                'context': '1M',
                'speed': 'Fast',
                'priority': 7,
                'supports_text': True,
                'supports_vision': True,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Google reasoning model with explicit thought process, zero cost.'
            },
            {
                'model_id': 'mistralai/mistral-7b-instruct:free',
                'display_name': 'Mistral 7B Instruct (Free)',
                'tier': 'free',
                'context': '32k',
                'speed': 'Instant',
                'priority': 8,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': False,
                'supports_structured_output': True,
                'desc': 'Lightweight, ultra-responsive workhorse for basic classifications and extraction.'
            },
            {
                'model_id': 'qwen/qwen-2.5-coder-32b-instruct:free',
                'display_name': 'Qwen 2.5 Coder 32B (Free)',
                'tier': 'free',
                'context': '32k',
                'speed': 'Fast',
                'priority': 9,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Alibaba top open-source coding and structured JSON model.'
            }
        ],
        'best': [
            {
                'model_id': 'google/gemini-2.5-pro',
                'display_name': 'Google Gemini 2.5 Pro',
                'tier': 'best',
                'context': '2M',
                'speed': 'Fast',
                'priority': 1,
                'supports_text': True,
                'supports_vision': True,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Massive 2M context, premier multimodal vision understanding and tool handling.'
            },
            {
                'model_id': 'anthropic/claude-3.5-sonnet',
                'display_name': 'Claude 3.5 Sonnet',
                'tier': 'best',
                'context': '200k',
                'speed': 'Fast',
                'priority': 2,
                'supports_text': True,
                'supports_vision': True,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Top-rated AI model worldwide for complex instruction following and website generation.'
            },
            {
                'model_id': 'openai/gpt-4o-mini',
                'display_name': 'GPT-4o Mini',
                'tier': 'best',
                'context': '128k',
                'speed': 'Very Fast',
                'priority': 3,
                'supports_text': True,
                'supports_vision': True,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'High intelligence, low latency, exceptionally low pricing for continuous sales pipelines.'
            },
            {
                'model_id': 'deepseek/deepseek-chat',
                'display_name': 'DeepSeek V3 (Chat)',
                'tier': 'best',
                'context': '64k',
                'speed': 'Fast',
                'priority': 4,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Frontier-grade performance at 1/10th the cost of commercial models.'
            }
        ],
        'pro': [
            {
                'model_id': 'openai/gpt-4o',
                'display_name': 'OpenAI GPT-4o (Omni)',
                'tier': 'pro',
                'context': '128k',
                'speed': 'Fast',
                'priority': 1,
                'supports_text': True,
                'supports_vision': True,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'OpenAI premier multimodal flagship with best-in-class vision and structured outputs.'
            },
            {
                'model_id': 'openai/o1-preview',
                'display_name': 'OpenAI o1-Preview',
                'tier': 'pro',
                'context': '128k',
                'speed': 'Deliberate',
                'priority': 5,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': False,
                'supports_structured_output': True,
                'desc': 'Deep autonomous reasoning system for complex logic and architectural design.'
            },
            {
                'model_id': 'anthropic/claude-3-opus',
                'display_name': 'Claude 3 Opus',
                'tier': 'pro',
                'context': '200k',
                'speed': 'Deliberate',
                'priority': 3,
                'supports_text': True,
                'supports_vision': True,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Deep contextual nuances and top-tier copywriting for high-ticket enterprise sales.'
            }
        ]
    }

    # Adjust for Groq if provider is Groq
    if 'groq' in p_name:
        catalog['free'] = [
            {
                'model_id': 'llama-3.3-70b-versatile',
                'display_name': 'Groq Llama 3.3 70B Versatile',
                'tier': 'free',
                'context': '128k',
                'speed': 'Ultra Fast (300+ t/s)',
                'priority': 1,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Groq LPU hardware acceleration, incredible speed, free rate limit tier.'
            },
            {
                'model_id': 'llama-3.1-8b-instant',
                'display_name': 'Groq Llama 3.1 8B Instant',
                'tier': 'free',
                'context': '128k',
                'speed': 'Instantaneous (800+ t/s)',
                'priority': 2,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Lightning fast response times under 200ms.'
            },
            {
                'model_id': 'mixtral-8x7b-32768',
                'display_name': 'Groq Mixtral 8x7B',
                'tier': 'free',
                'context': '32k',
                'speed': 'Ultra Fast',
                'priority': 3,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'MoE architecture with balanced general performance.'
            }
        ]
        catalog['best'] = catalog['free']
        catalog['pro'] = [
            {
                'model_id': 'llama-3.3-70b-specdec',
                'display_name': 'Groq Llama 3.3 70B SpecDec',
                'tier': 'pro',
                'context': '8k',
                'speed': 'Maximum Velocity',
                'priority': 1,
                'supports_text': True,
                'supports_vision': False,
                'supports_tool_calling': True,
                'supports_structured_output': True,
                'desc': 'Speculative decoding hardware execution on Groq LPUs.'
            }
        ]

    # Mark which models are already added for this provider
    existing_model_ids = {m.model_id for m in provider.models}
    for category in catalog.values():
        for m in category:
            m['already_added'] = m['model_id'] in existing_model_ids

    return jsonify({
        'success': True,
        'provider_name': provider.name,
        'catalog': catalog
    })


@models_bp.route('/providers/<int:provider_id>/models/quick-add', methods=['POST'])
@login_required
def quick_add_model(provider_id):
    """1-Click add discovered model or bulk add top free tier models."""
    provider = LLMProvider.query.get_or_404(provider_id)
    action = request.form.get('action') or (request.json or {}).get('action')

    if action == 'add_top_free':
        # Auto-register top 3 free models
        p_name = (provider.name or '').lower()
        free_presets = [
            ('meta-llama/llama-3.3-70b-instruct:free', 'Llama 3.3 70B (Free)', 5, True, False, True, True),
            ('google/gemini-2.0-flash-exp:free', 'Gemini 2.0 Flash (Free)', 4, True, True, True, True),
            ('deepseek/deepseek-r1:free', 'DeepSeek R1 (Free)', 6, True, False, False, True),
        ]
        if 'groq' in p_name:
            free_presets = [
                ('llama-3.3-70b-versatile', 'Groq Llama 3.3 70B', 1, True, False, True, True),
                ('llama-3.1-8b-instant', 'Groq Llama 3.1 8B', 2, True, False, True, True),
            ]

        added_count = 0
        existing = {m.model_id for m in provider.models}
        for mid, dname, prio, txt, vis, tools, jsn in free_presets:
            if mid not in existing:
                m = LLMModel(
                    provider_id=provider_id,
                    model_id=mid,
                    display_name=dname,
                    priority=prio,
                    supports_text=txt,
                    supports_vision=vis,
                    supports_tool_calling=tools,
                    supports_structured_output=jsn,
                    is_enabled=True
                )
                db.session.add(m)
                added_count += 1
        db.session.commit()
        flash(f"⚡ Added {added_count} top free models to {provider.name} with auto-configured capabilities!", "success")
        return redirect(url_for('models.index', provider_id=provider_id))

    # Single quick add
    model_id = sanitize_string(request.form.get('model_id') or (request.json or {}).get('model_id', ''))
    display_name = sanitize_string(request.form.get('display_name') or (request.json or {}).get('display_name', ''))
    priority = int(request.form.get('priority') or (request.json or {}).get('priority', 10))
    supports_text = (request.form.get('supports_text') in ['on', 'true', True] or (request.json or {}).get('supports_text', True))
    supports_vision = (request.form.get('supports_vision') in ['on', 'true', True] or (request.json or {}).get('supports_vision', False))
    supports_tool_calling = (request.form.get('supports_tool_calling') in ['on', 'true', True] or (request.json or {}).get('supports_tool_calling', False))
    supports_structured_output = (request.form.get('supports_structured_output') in ['on', 'true', True] or (request.json or {}).get('supports_structured_output', True))

    if not model_id:
        flash("Model ID is required.", "error")
        return redirect(url_for('models.index', provider_id=provider_id))

    # Check if already exists
    existing = LLMModel.query.filter_by(provider_id=provider_id, model_id=model_id).first()
    if existing:
        flash(f"Model '{model_id}' is already configured.", "info")
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

    if request.is_json:
        return jsonify({'success': True, 'message': f"Model '{model.display_name}' added successfully."})

    flash(f"Model '{model.display_name}' added successfully to {provider.name}.", "success")
    return redirect(url_for('models.index', provider_id=provider_id))

