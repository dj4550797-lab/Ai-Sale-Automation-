"""
Flixora AI Sales Automation Agent — Knowledge Base Tests
"""
import pytest
from app import create_app
from app.extensions import db
from app.models import KnowledgeBase
from app.services.auth_service import create_admin_user
from app.services.knowledge_service import (
    create_kb_entry, update_kb_entry, delete_kb_entry, list_kb_entries
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Seed test admin
        create_admin_user(username='testadmin', email='test@flixora.com', password='password')
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_kb_crud_services(app):
    """Test standard knowledge base CRUD services."""
    with app.app_context():
        # Create
        res_create = create_kb_entry('faqs', 'Refund Policy', 'We offer a 14 day refund.', is_enabled=True)
        assert res_create['success'] is True
        entry_id = res_create['entry_id']

        # List
        entries = list_kb_entries(category='faqs')
        assert len(entries) == 1
        assert entries[0].title == 'Refund Policy'

        # Update
        res_update = update_kb_entry(entry_id, 'faqs', 'Refund Policy V2', 'We offer a 30 day refund.', is_enabled=False)
        assert res_update['success'] is True
        
        db.session.commit()
        entry = KnowledgeBase.query.get(entry_id)
        assert entry.title == 'Refund Policy V2'
        assert entry.is_enabled is False

        # Delete
        res_delete = delete_kb_entry(entry_id)
        assert res_delete['success'] is True
        assert KnowledgeBase.query.get(entry_id) is None


def test_kb_toggle_route(client, app):
    """Test AJAX toggle route."""
    # Login
    client.post('/login', data={'username': 'testadmin', 'password': 'password'})
    
    with app.app_context():
        entry = KnowledgeBase(category='faqs', title='Pricing Rules', content='Fixed pricing.', is_enabled=True)
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id

    # Toggle off
    response = client.post(f'/knowledge/toggle/{entry_id}')
    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['is_enabled'] is False

    with app.app_context():
        db_entry = KnowledgeBase.query.get(entry_id)
        assert db_entry.is_enabled is False
