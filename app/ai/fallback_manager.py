"""
Flixora AI Sales Automation Agent — Fallback Manager

Implements capability-based routing and priority-based fallback logic (§64-67).
"""
from datetime import datetime, timezone
from app.extensions import db
from app.models import LLMProvider, LLMModel
from app.constants import ProviderStatus
from app.services.llm_service import get_adapter_for_provider
from app.utils.logger import get_logger

logger = get_logger('ai')


class LLMFallbackManager:
    """Manages LLM fallback paths across Provider + Model nodes."""

    def resolve_routing_nodes(self, capability):
        """Find and prioritize active provider/model nodes supporting capability."""
        # Query active models where the provider is enabled and status is not disabled/unavailable
        query = db.session.query(LLMModel, LLMProvider).join(
            LLMProvider, LLMModel.provider_id == LLMProvider.id
        ).filter(
            LLMModel.is_enabled == True,
            LLMProvider.is_enabled == True,
            LLMProvider.status != ProviderStatus.DISABLED
        )

        # Filter by required capability (§130)
        if capability == 'text':
            query = query.filter(LLMModel.supports_text == True)
        elif capability == 'vision':
            query = query.filter(LLMModel.supports_vision == True)
        elif capability == 'tool_calling':
            query = query.filter(LLMModel.supports_tool_calling == True)
        elif capability == 'structured_output':
            query = query.filter(LLMModel.supports_structured_output == True)

        nodes = query.all()

        # Sort by provider priority (ascending), then model priority (ascending) (§67)
        # e.g., priority=1 runs before priority=2
        nodes.sort(key=lambda x: (x[1].priority, x[0].priority))
        return nodes

    def execute_with_fallback(self, capability, prompt, response_schema=None, options=None):
        """Execute request, falling back across matching nodes on failure."""
        options = options or {}
        nodes = self.resolve_routing_nodes(capability)

        if not nodes:
            raise ValueError(f"No enabled LLM provider/model found with capability: {capability}")

        last_error = None
        for model, provider in nodes:
            logger.info(f"Routing request via Node: {provider.name} -> {model.model_id}")
            
            try:
                adapter = get_adapter_for_provider(provider)
                start_time = datetime.now()

                # Call appropriate adapter method
                if response_schema:
                    result = adapter.generate_structured_output(
                        model_id=model.model_id,
                        prompt=prompt,
                        response_schema=response_schema,
                        options=options
                    )
                else:
                    result = adapter.generate_text(
                        model_id=model.model_id,
                        prompt=prompt,
                        options=options
                    )

                # Update metrics on success
                latency = (datetime.now() - start_time).total_seconds() * 1000
                model.last_used_at = datetime.now(timezone.utc)
                model.total_requests += 1
                provider.last_request_at = datetime.now(timezone.utc)
                provider.request_count += 1
                provider.status = ProviderStatus.HEALTHY
                
                db.session.commit()
                return result

            except Exception as e:
                logger.warning(
                    f"Failure on node {provider.name} ({model.model_id}): {e}. "
                    "Attempting fallback..."
                )
                # Update metrics on failure
                model.total_failures += 1
                provider.last_error_at = datetime.now(timezone.utc)
                provider.last_error_message = str(e)
                provider.failure_count += 1
                provider.fallback_count += 1
                provider.status = ProviderStatus.WARNING
                
                db.session.commit()
                last_error = e

        raise RuntimeError(f"All LLM fallback paths failed. Last error: {last_error}")


# Global fallback manager instance
fallback_manager = LLMFallbackManager()
