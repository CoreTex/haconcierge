import httpx
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AIClient:
    """OpenAI-compatible HTTP client – works with Ollama, LM Studio, and any OpenAI API."""

    def __init__(self, base_url: str, model: str, timeout: int = 30, temperature: float = 0.1):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature

    async def chat(self, messages: list[dict], system: Optional[str] = None) -> Optional[str]:
        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": self.temperature,
            "stream": False,
        }

        # Ollama uses /api/chat, OpenAI uses /v1/chat/completions
        endpoint = f"{self.base_url}/api/chat"
        if "/v1" in self.base_url or "openai" in self.base_url.lower():
            endpoint = f"{self.base_url}/v1/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # Ollama response format
            if "message" in data:
                return data["message"]["content"]
            # OpenAI response format
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
        except httpx.ConnectError:
            logger.error("AI endpoint not reachable: %s", self.base_url)
        except httpx.TimeoutException:
            logger.error("AI request timed out after %ds", self.timeout)
        except Exception as e:
            logger.error("AI request failed: %s", e)
        return None

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Try Ollama endpoint first
                try:
                    resp = await client.get(f"{self.base_url}/api/tags")
                    if resp.status_code == 200:
                        data = resp.json()
                        return [m["name"] for m in data.get("models", [])]
                except Exception:
                    pass
                # Try OpenAI endpoint
                try:
                    resp = await client.get(f"{self.base_url}/v1/models")
                    if resp.status_code == 200:
                        data = resp.json()
                        return [m["id"] for m in data.get("data", [])]
                except Exception:
                    pass
        except Exception as e:
            logger.error("Failed to list models: %s", e)
        return []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
