import httpx
import json
from backend.config import settings


class LLMClient:
    """Thin wrapper around the LLM provider. Only Ollama is wired up for now —
    this is the one file to change if you switch providers later."""

    def __init__(self):
        self.base_url = settings.llm_base_url
        self.model = settings.llm_model

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Calls the LLM and forces a JSON-only response. Returns a parsed dict."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "system": system_prompt,
                    "prompt": user_prompt,
                    "format": "json",
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw_text = data.get("response", "{}")
            return json.loads(raw_text)