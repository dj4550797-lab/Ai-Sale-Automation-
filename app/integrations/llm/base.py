"""
Flixora AI Sales Automation Agent — LLM Base Adapter

Defines the interface for all external LLM provider integrations.
"""
from abc import ABC, abstractmethod


class BaseLLMAdapter(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, api_key, base_url=None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def test_connection(self):
        """Test connection to the provider. Returns dict with status info."""
        pass

    @abstractmethod
    def generate_text(self, model_id, prompt, options=None):
        """Generate text from a prompt. Options contains max_tokens, temp, etc."""
        pass

    @abstractmethod
    def generate_structured_output(self, model_id, prompt, response_schema, options=None):
        """Generate structured JSON output validated against response_schema."""
        pass
