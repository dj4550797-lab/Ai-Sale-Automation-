"""
Flixora AI Sales Automation Agent — LLM Fallback & Routing Tests
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import LLMProvider, LLMModel
from app.constants import ProviderStatus, LLMProtocol
from app.services.llm_service import save_provider_credential
from app.ai.fallback_manager import fallback_manager


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_fallback_success_flow(app):
    """Test successful fallback from failing priority 1 node to working priority 2 node."""
    with app.app_context():
        # 1. Setup Provider A (Priority 1)
        prov_a = LLMProvider(name='OpenRouter-A', protocol=LLMProtocol.OPENAI_COMPATIBLE, priority=1, status=ProviderStatus.HEALTHY)
        db.session.add(prov_a)
        db.session.commit()
        save_provider_credential(prov_a.id, 'key-a')
        
        model_a = LLMModel(provider_id=prov_a.id, model_id='openai/gpt-4', is_enabled=True, priority=1, supports_text=True)
        db.session.add(model_a)
        
        # 2. Setup Provider B (Priority 2)
        prov_b = LLMProvider(name='OpenRouter-B', protocol=LLMProtocol.OPENAI_COMPATIBLE, priority=2, status=ProviderStatus.HEALTHY)
        db.session.add(prov_b)
        db.session.commit()
        save_provider_credential(prov_b.id, 'key-b')
        
        model_b = LLMModel(provider_id=prov_b.id, model_id='openai/gpt-4', is_enabled=True, priority=1, supports_text=True)
        db.session.add(model_b)
        db.session.commit()

        # Mock adapter responses: Adapter A raises error, Adapter B returns text
        def mock_get_adapter(provider):
            mock_adapter = MagicMock()
            if provider.id == prov_a.id:
                mock_adapter.generate_text.side_effect = RuntimeError("API rate limit exceeded")
            else:
                mock_adapter.generate_text.return_value = "Success from B!"
            return mock_adapter

        with patch('app.ai.fallback_manager.get_adapter_for_provider', side_effect=mock_get_adapter):
            result = fallback_manager.execute_with_fallback('text', 'Hello')
            
            # Should fall back and return B's response
            assert result == "Success from B!"
            
            # Assert metrics updated in DB
            db.session.refresh(prov_a)
            db.session.refresh(prov_b)
            db.session.refresh(model_a)
            db.session.refresh(model_b)
            
            assert prov_a.fallback_count == 1
            assert prov_a.failure_count == 1
            assert prov_a.status == ProviderStatus.WARNING
            
            assert prov_b.request_count == 1
            assert prov_b.status == ProviderStatus.HEALTHY
            assert model_b.total_requests == 1


def test_capability_routing(app):
    """Test that models are filtered by required capabilities (e.g. vision)."""
    with app.app_context():
        # Setup Provider with text-only model
        prov = LLMProvider(name='OpenRouter', protocol=LLMProtocol.OPENAI_COMPATIBLE, priority=1, status=ProviderStatus.HEALTHY)
        db.session.add(prov)
        db.session.commit()
        save_provider_credential(prov.id, 'key')
        
        text_model = LLMModel(
            provider_id=prov.id,
            model_id='openai/text-model',
            is_enabled=True,
            supports_text=True,
            supports_vision=False
        )
        db.session.add(text_model)
        
        # Setup Provider with vision-capable model
        vision_model = LLMModel(
            provider_id=prov.id,
            model_id='openai/vision-model',
            is_enabled=True,
            supports_text=True,
            supports_vision=True
        )
        db.session.add(vision_model)
        db.session.commit()

        # Run text routing
        nodes = fallback_manager.resolve_routing_nodes('text')
        assert len(nodes) == 2  # Both models support text
        
        # Run vision routing
        nodes_vision = fallback_manager.resolve_routing_nodes('vision')
        assert len(nodes_vision) == 1
        assert nodes_vision[0][0].model_id == 'openai/vision-model'  # Only vision model routed
