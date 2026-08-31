"""
Flixora AI Sales Automation Agent — OpenAI Compatible LLM Adapter

Handles OpenRouter and generic OpenAI-compatible completions via HTTP.
"""
import requests
import json
from app.integrations.llm.base import BaseLLMAdapter
from app.utils.logger import get_logger

logger = get_logger('ai')


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """Adapter for OpenRouter / OpenAI compatible providers."""

    def test_connection(self):
        """Test API key validity by querying available models or a cheap endpoint."""
        url = f"{self.base_url or 'https://api.openai.com/v1'}/models"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        try:
            # Special headers for OpenRouter
            if "openrouter" in url.lower():
                headers["HTTP-Referer"] = "https://flixora.com"
                headers["X-Title"] = "Flixora Sales Agent"

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                # Return success and some available models
                models = [m['id'] for m in models_data.get('data', [])[:5]]
                return {
                    "success": True,
                    "models": models,
                    "message": "Connection successful."
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status code {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_text(self, model_id, prompt, options=None):
        """Generate chat completion."""
        options = options or {}
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        if "openrouter" in url.lower():
            headers["HTTP-Referer"] = "https://flixora.com"
            headers["X-Title"] = "Flixora Sales Agent"

        payload = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": options.get("temperature", 0.7),
            "max_tokens": options.get("max_tokens", 1000)
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                return res_data['choices'][0]['message']['content'].strip()
            else:
                raise ValueError(f"Provider error: status code {response.status_code}, response: {response.text}")
        except Exception as e:
            logger.error(f"OpenAI compatible request failed: {e}")
            raise e

    def generate_structured_output(self, model_id, prompt, response_schema, options=None):
        """Generate structured completion using JSON Mode or system instructions."""
        options = options or {}
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        if "openrouter" in url.lower():
            headers["HTTP-Referer"] = "https://flixora.com"
            headers["X-Title"] = "Flixora Sales Agent"

        # Ask the model to return JSON matching the schema
        system_instructions = (
            "You are a helpful assistant. You must output JSON only. "
            f"The output must match this schema strictly: {json.dumps(response_schema)}"
        )

        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": prompt}
            ],
            "temperature": options.get("temperature", 0.2),
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                content = res_data['choices'][0]['message']['content'].strip()
                # Parse JSON to validate
                return json.loads(content)
            else:
                raise ValueError(f"Provider error: status code {response.status_code}, response: {response.text}")
        except Exception as e:
            logger.error(f"OpenAI compatible structured output failed: {e}")
            raise e
