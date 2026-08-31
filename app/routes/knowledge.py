"""
Flixora AI Sales Automation Agent — Knowledge Base Routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required

from app.extensions import db
from app.models import KnowledgeBase
from app.constants import KBCategory
from app.services.knowledge_service import (
    create_kb_entry, update_kb_entry, delete_kb_entry, list_kb_entries
)
from app.security.validation import sanitize_string

knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/knowledge')


@knowledge_bp.route('')
@login_required
def index():
    """List all knowledge base entries, sorted by category."""
    category_filter = sanitize_string(request.args.get('category', ''))
    
    entries = list_kb_entries(category=category_filter if category_filter else None)
    
    # Organize entries by category for index view tab layout
    categorized_entries = {cat: [] for cat in KBCategory.ALL}
    for entry in entries:
        if entry.category in categorized_entries:
            categorized_entries[entry.category].append(entry)
            
    return render_template('knowledge/index.html',
                           categorized_entries=categorized_entries,
                           categories=KBCategory.ALL,
                           selected_category=category_filter)


@knowledge_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Create a new knowledge base entry."""
    category = sanitize_string(request.form.get('category', ''))
    title = sanitize_string(request.form.get('title', ''))
    content = request.form.get('content', '')  # Allow newline structures, sanitize if needed
    is_enabled = request.form.get('is_enabled') == 'on'

    if not category or not title or not content:
        flash("Please fill in all required fields.", "error")
        return redirect(url_for('knowledge.index'))

    res = create_kb_entry(category, title, content, is_enabled)
    if res.get('success'):
        flash(f"Knowledge entry '{title}' added successfully.", "success")
    else:
        flash(f"Failed to add entry: {res.get('error')}", "error")

    return redirect(url_for('knowledge.index', category=category))


@knowledge_bp.route('/edit/<int:id>', methods=['POST'])
@login_required
def edit(id):
    """Edit an existing knowledge base entry."""
    category = sanitize_string(request.form.get('category', ''))
    title = sanitize_string(request.form.get('title', ''))
    content = request.form.get('content', '')
    is_enabled = request.form.get('is_enabled') == 'on'

    if not category or not title or not content:
        flash("Please fill in all required fields.", "error")
        return redirect(url_for('knowledge.index'))

    res = update_kb_entry(id, category, title, content, is_enabled)
    if res.get('success'):
        flash("Knowledge entry updated successfully.", "success")
    else:
        flash(f"Failed to update entry: {res.get('error')}", "error")

    return redirect(url_for('knowledge.index', category=category))


@knowledge_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete a knowledge base entry."""
    # Find entry first to get category for redirect
    entry = KnowledgeBase.query.get_or_404(id)
    category = entry.category
    
    res = delete_kb_entry(id)
    if res.get('success'):
        flash("Knowledge entry deleted successfully.", "success")
    else:
        flash(f"Failed to delete entry: {res.get('error')}", "error")

    return redirect(url_for('knowledge.index', category=category))


@knowledge_bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle(id):
    """API endpoint to quick toggle the active state of a knowledge base item."""
    try:
        entry = KnowledgeBase.query.get_or_404(id)
        entry.is_enabled = not entry.is_enabled
        db.session.commit()
        return jsonify({
            "success": True,
            "is_enabled": entry.is_enabled,
            "message": f"Entry state set to {'enabled' if entry.is_enabled else 'disabled'}."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
