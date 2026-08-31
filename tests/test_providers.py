"""
Flixora AI Sales Automation Agent — LLM Provider Management Tests
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import LLMProvider, LLMModel, APICredential
from app.constants import ProviderStatus, LLMProtocol
from app.services.auth_service import create_admin_user
from app.services.llm_service import save_provider_credential, test_provider_connection as service_test_provider_connection


@pytest.fixture
def app():
    """Create app instance configured for testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        # Seed test admin
        create_admin_user(
            username='testadmin',
            email='testadmin@flixora.com',
            password='password123'
        )
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_add_provider_and_credential(client, app):
    """Test adding provider and encrypting credentials."""
    # Logout first to clear session leak
    client.get('/logout')
    # Login
    client.post('/login', data={'username': 'testadmin', 'password': 'password123'})
    
    response = client.post('/settings/llm/providers/add', data={
        'name': 'Test OpenRouter',
        'protocol': LLMProtocol.OPENAI_COMPATIBLE,
        'base_url': 'https://openrouter.example.com',
        'priority': 2,
        'api_key': 'test-openrouter-key-12345'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        provider = LLMProvider.query.filter_by(name='Test OpenRouter').first()
        assert provider is not None
        assert provider.protocol == LLMProtocol.OPENAI_COMPATIBLE
        assert provider.priority == 2
        
        # Verify credential encrypted
        cred = APICredential.query.filter_by(provider_id=provider.id).first()
        assert cred is not None
        assert cred.last_four == '2345'
        assert cred.encrypted_value != 'test-openrouter-key-12345'
        
        # Verify decryption works
        from app.security.encryption import decrypt_value
        decrypted = decrypt_value(cred.encrypted_value)
        assert decrypted == 'test-openrouter-key-12345'


def test_add_model_capabilities(client, app):
    """Test adding model and capability flags."""
    # Logout first to clear session leak
    client.get('/logout')
    # Login
    client.post('/login', data={'username': 'testadmin', 'password': 'password123'})
    
    # Create provider first
    with app.app_context():
        provider = LLMProvider(name='OpenAI', protocol=LLMProtocol.OPENAI_COMPATIBLE)
        db.session.add(provider)
        db.session.commit()
        provider_id = provider.id
        
    response = client.post(f'/settings/llm/providers/{provider_id}/models/add', data={
        'model_id': 'openai/gpt-4',
        'display_name': 'GPT 4',
        'priority': 5,
        'supports_text': 'on',
        'supports_structured_output': 'on'
        # supports_vision and supports_tool_calling are off
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        model = LLMModel.query.filter_by(model_id='openai/gpt-4').first()
        assert model is not None
        assert model.display_name == 'GPT 4'
        assert model.priority == 5
        assert model.supports_text is True
        assert model.supports_structured_output is True
        assert model.supports_vision is False
        assert model.supports_tool_calling is False


@patch('app.integrations.llm.openai_compatible.OpenAICompatibleAdapter.test_connection')
def test_provider_connection_service(mock_test, app):
    """Test provider connection service testing logic."""
    mock_test.return_value = {
        "success": True,
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "message": "Connection successful."
    }
    
    with app.app_context():
        # Setup provider and credential
        provider = LLMProvider(name='OpenRouter', protocol=LLMProtocol.OPENAI_COMPATIBLE)
        db.session.add(provider)
        db.session.commit()
        
        save_provider_credential(provider.id, 'test-key')
        
        # Test connection
        res = service_test_provider_connection(provider.id)
        assert res['success'] is True
        assert 'gpt-4' in res['models']
        
        # Assert status updated in DB
        assert provider.status == ProviderStatus.HEALTHY
        
        cred = APICredential.query.filter_by(provider_id=provider.id).first()
        assert cred.is_valid is True
