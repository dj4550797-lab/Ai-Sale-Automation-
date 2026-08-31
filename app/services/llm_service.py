"""
Flixora AI Sales Automation Agent — LLM Service

Manages LLM providers, models, and adapter instantiations.
"""
from datetime import datetime, timezone
from app.extensions import db
from app.models import LLMProvider, LLMModel, APICredential
from app.constants import ProviderStatus, LLMProtocol
from app.security.encryption import decrypt_value, encrypt_value
from app.utils.logger import get_logger

logger = get_logger('ai')


def get_adapter_for_provider(provider):
    """Instantiate the appropriate LLM adapter for a provider."""
    # Find active credential for this provider
    cred = APICredential.query.filter_by(
        provider_id=provider.id,
        credential_type='api_key'
    ).first()

    if not cred:
        # Fallback to general API key by service name
        cred = APICredential.query.filter_by(
            service_name=provider.name.lower(),
            credential_type='api_key'
        ).first()

    if not cred:
        raise ValueError(f"No API key credential found for provider: {provider.name}")

    api_key = decrypt_value(cred.encrypted_value)

    if provider.protocol == LLMProtocol.OPENAI_COMPATIBLE:
        from app.integrations.llm.openai_compatible import OpenAICompatibleAdapter
        return OpenAICompatibleAdapter(api_key=api_key, base_url=provider.base_url)
    elif provider.protocol == LLMProtocol.GEMINI:
        from app.integrations.llm.google_ai import GoogleAIAdapter
        return GoogleAIAdapter(api_key=api_key)
    else:
        raise ValueError(f"Unsupported LLM protocol: {provider.protocol}")


def test_provider_connection(provider_id):
    """Decrypt credential and run connection test."""
    provider = LLMProvider.query.get(provider_id)
    if not provider:
        raise ValueError("Provider not found")

    try:
        adapter = get_adapter_for_provider(provider)
        start_time = datetime.now()
        res = adapter.test_connection()
        latency = (datetime.now() - start_time).total_seconds() * 1000

        provider.last_request_at = datetime.now(timezone.utc)
        provider.request_count += 1

        # Find credential to update status
        cred = APICredential.query.filter_by(
            provider_id=provider.id,
            credential_type='api_key'
        ).first()

        if res.get("success"):
            provider.status = ProviderStatus.HEALTHY
            if cred:
                cred.is_valid = True
                cred.last_tested_at = datetime.now(timezone.utc)
                cred.last_error = ''
            db.session.commit()
            return {
                "success": True,
                "latency_ms": int(latency),
                "models": res.get("models", []),
                "message": "Connection successful."
            }
        else:
            provider.status = ProviderStatus.WARNING
            provider.failure_count += 1
            provider.last_error_at = datetime.now(timezone.utc)
            provider.last_error_message = res.get("error", "Unknown error")
            if cred:
                cred.is_valid = False
                cred.last_tested_at = datetime.now(timezone.utc)
                cred.last_error = res.get("error", "Unknown error")
            db.session.commit()
            return {
                "success": False,
                "error": res.get("error", "Unknown error")
            }
    except Exception as e:
        logger.error(f"Failed to test connection for provider {provider_id}: {e}")
        provider.status = ProviderStatus.UNAVAILABLE
        provider.failure_count += 1
        provider.last_error_at = datetime.now(timezone.utc)
        provider.last_error_message = str(e)
        db.session.commit()
        return {
            "success": False,
            "error": str(e)
        }


def save_provider_credential(provider_id, api_key):
    """Encrypt and save API key credential for provider."""
    provider = LLMProvider.query.get(provider_id)
    if not provider:
        raise ValueError("Provider not found")

    encrypted = encrypt_value(api_key)
    last_four = api_key[-4:] if len(api_key) >= 4 else api_key

    # Check if credential already exists
    cred = APICredential.query.filter_by(
        provider_id=provider.id,
        credential_type='api_key'
    ).first()

    if cred:
        cred.encrypted_value = encrypted
        cred.last_four = last_four
        cred.updated_at = datetime.now(timezone.utc)
    else:
        cred = APICredential(
            provider_id=provider.id,
            credential_type='api_key',
            service_name=provider.name.lower(),
            encrypted_value=encrypted,
            last_four=last_four
        )
        db.session.add(cred)

    db.session.commit()
    return cred
