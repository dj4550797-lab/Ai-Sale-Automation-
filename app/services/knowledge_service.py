"""
Flixora AI Sales Automation Agent — Knowledge Service
"""
from datetime import datetime, timezone
from app.extensions import db
from app.models import KnowledgeBase
from app.utils.logger import get_logger

logger = get_logger('services')


def create_kb_entry(category, title, content, is_enabled=True):
    """Create a new knowledge base entry."""
    try:
        # Determine sort order (append to end)
        max_order = db.session.query(db.func.max(KnowledgeBase.sort_order)).filter_by(category=category).scalar() or 0
        
        entry = KnowledgeBase(
            category=category,
            title=title,
            content=content,
            is_enabled=is_enabled,
            sort_order=max_order + 1
        )
        db.session.add(entry)
        db.session.commit()
        logger.info(f"Knowledge base entry created: [{category}] '{title}'")
        return {"success": True, "entry_id": entry.id}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating kb entry: {e}")
        return {"success": False, "error": str(e)}


def update_kb_entry(entry_id, category, title, content, is_enabled):
    """Update an existing knowledge base entry."""
    try:
        entry = KnowledgeBase.query.get(entry_id)
        if not entry:
            return {"success": False, "error": f"Entry with ID {entry_id} not found."}
            
        entry.category = category
        entry.title = title
        entry.content = content
        entry.is_enabled = is_enabled
        entry.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        logger.info(f"Knowledge base entry updated: [{category}] '{title}'")
        return {"success": True, "entry_id": entry.id}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating kb entry {entry_id}: {e}")
        return {"success": False, "error": str(e)}


def delete_kb_entry(entry_id):
    """Delete a knowledge base entry."""
    try:
        entry = KnowledgeBase.query.get(entry_id)
        if not entry:
            return {"success": False, "error": f"Entry with ID {entry_id} not found."}
            
        title = entry.title
        category = entry.category
        
        db.session.delete(entry)
        db.session.commit()
        logger.info(f"Knowledge base entry deleted: [{category}] '{title}'")
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting kb entry {entry_id}: {e}")
        return {"success": False, "error": str(e)}


def list_kb_entries(category=None):
    """List all knowledge base entries, optionally filtered by category."""
    query = KnowledgeBase.query
    if category:
        query = query.filter_by(category=category)
    return query.order_by(KnowledgeBase.sort_order.asc(), KnowledgeBase.created_at.desc()).all()
