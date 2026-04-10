import httpx

from src.infrastructure.llm.client import LLMClient

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class ClaudeClient(LLMClient):
    def __init__(self, api_key: str, model: str = "claude-opus-4-6", timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["content"][0]["text"]
