"""
Flixora AI Sales Automation Agent — Google Gemini Adapter

Direct REST integration with Google AI Gemini API.
"""
import requests
import json
from app.integrations.llm.base import BaseLLMAdapter
from app.utils.logger import get_logger

logger = get_logger('ai')


class GoogleAIAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini API."""

    def test_connection(self):
        """Test API key by fetching a list of models."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                models = [m['name'].replace('models/', '') for m in models_data.get('models', [])[:5]]
                return {
                    "success": True,
                    "models": models,
                    "message": "Connection successful."
                }
            else:
                return {
                    "success": False,
                    "error": f"Gemini API returned status code {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_text(self, model_id, prompt, options=None):
        """Generate content from Gemini models."""
        options = options or {}
        # Make sure model name doesn't contain models/ prefix twice
        model_name = model_id.replace('models/', '')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": options.get("temperature", 0.7),
                "maxOutputTokens": options.get("max_tokens", 1000)
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                candidate = res_data.get('candidates', [{}])[0]
                content = candidate.get('content', {})
                parts = content.get('parts', [{}])
                text = parts[0].get('text', '')
                if text:
                    return text.strip()
                raise ValueError(f"Empty response from Gemini API: {response.text}")
            else:
                raise ValueError(f"Gemini API error: status {response.status_code}, response: {response.text}")
        except Exception as e:
            logger.error(f"Gemini request failed: {e}")
            raise e

    def generate_structured_output(self, model_id, prompt, response_schema, options=None):
        """Generate structured JSON matching the schema from Gemini."""
        options = options or {}
        model_name = model_id.replace('models/', '')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

        headers = {
            "Content-Type": "application/json"
        }

        # Request JSON output
        payload = {
            "contents": [{
                "parts": [{"text": f"{prompt}\nReturn JSON strictly matching this schema: {json.dumps(response_schema)}"}]
            }],
            "generationConfig": {
                "temperature": options.get("temperature", 0.2),
                "responseMimeType": "application/json"
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                candidate = res_data.get('candidates', [{}])[0]
                content = candidate.get('content', {})
                parts = content.get('parts', [{}])
                text = parts[0].get('text', '')
                if text:
                    return json.loads(text.strip())
                raise ValueError(f"Empty response from Gemini API: {response.text}")
            else:
                raise ValueError(f"Gemini API error: status {response.status_code}, response: {response.text}")
        except Exception as e:
            logger.error(f"Gemini structured output failed: {e}")
            raise e
