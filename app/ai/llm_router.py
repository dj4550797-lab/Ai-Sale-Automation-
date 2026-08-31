"""
Flixora AI Sales Automation Agent — LLM Router

Central entry point for all LLM tasks. Selects capability requirements (§68)
and passes requests to the Fallback Manager.
"""
from app.ai.fallback_manager import fallback_manager


class LLMRouter:
    """Orchestrates capability selection and fallback execution for AI tasks."""

    def generate_text(self, prompt, task_type='general', options=None):
        """Generate text using priority fallback router."""
        capability = 'text'
        
        # Override capability for specific task types
        if task_type == 'image_analysis':
            capability = 'vision'

        return fallback_manager.execute_with_fallback(
            capability=capability,
            prompt=prompt,
            response_schema=None,
            options=options
        )

    def generate_structured_output(self, prompt, response_schema, task_type='general', options=None):
        """Generate validated JSON matching a schema using fallback router."""
        # Use structured_output capability if supported, fallback to text JSON prompt engineering if needed.
        # Here we route to structured_output nodes.
        capability = 'structured_output'
        
        if task_type == 'image_analysis':
            capability = 'vision'

        return fallback_manager.execute_with_fallback(
            capability=capability,
            prompt=prompt,
            response_schema=response_schema,
            options=options
        )


# Global LLM router instance
llm_router = LLMRouter()
