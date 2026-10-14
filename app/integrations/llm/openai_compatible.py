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
        """Test API key validity by querying auth endpoint or models endpoint."""
        raw_key = (self.api_key or '').strip()
        base = (self.base_url or 'https://api.openai.com/v1').rstrip('/')

        # OpenRouter provides an auth endpoint that requires authentication
        # Unlike /models which is publicly accessible even with invalid keys!
        if "openrouter" in base.lower():
            url = f"{base}/auth/key"
            headers = {
                "Authorization": f"Bearer {raw_key}",
                "HTTP-Referer": "https://flixora.com",
                "X-Title": "Flixora Sales Agent"
            }
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    label = data.get('label') or 'OpenRouter Key'
                    usage = data.get('usage', 0)
                    limit = data.get('limit')
                    limit_str = f" / ${limit:.2f}" if limit is not None else ""
                    return {
                        "success": True,
                        "models": ["google/gemini-2.0-flash-exp:free", "deepseek/deepseek-r1:free"],
                        "message": f"Verified ({label})! Usage: ${usage:.2f}{limit_str}"
                    }
                else:
                    err_text = response.text
                    try:
                        err_json = response.json()
                        err_text = err_json.get('error', {}).get('message', err_text)
                    except Exception:
                        pass
                    return {
                        "success": False,
                        "error": f"OpenRouter rejected key (HTTP {response.status_code}): {err_text}"
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

        # Generic OpenAI compatible test
        url = f"{base}/models"
        headers = {
            "Authorization": f"Bearer {raw_key}"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                models_data = response.json()
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
        raw_key = (self.api_key or '').strip()
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {raw_key}"
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
        raw_key = (self.api_key or '').strip()
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {raw_key}"
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
