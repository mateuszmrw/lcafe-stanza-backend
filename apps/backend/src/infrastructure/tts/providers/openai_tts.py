"""OpenAITtsProvider — call any OpenAI-compatible audio server.

Works with any server that implements POST /v1/audio/speech.

Env vars:
    openai_tts_url       — base URL of the TTS server
    openai_tts_api_key   — bearer token (optional for local servers)
    openai_tts_model     — model id sent in the request payload
"""

from __future__ import annotations

import logging

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Languages and voices are tied to the specific TTS model configured via
# openai_tts_model. Adjust for the backend you point openai_tts_url at.
SUPPORTED_LANGUAGES = frozenset({"zh", "ko", "ru"})

_VOICE_MAP: dict[str, str] = {
    "zh": "Chelsie",
    "ko": "Cove",
    "ru": "Serena",
}
_DEFAULT_VOICE = "Serena"


class OpenAITtsProvider:
    def supports(self, language_code: str) -> bool:
        return language_code in SUPPORTED_LANGUAGES

    async def generate(self, text: str, language_code: str) -> bytes:
        """Generate speech audio. Returns raw MP3 bytes."""
        settings = get_settings()
        if not settings.openai_tts_url:
            raise RuntimeError("openai_tts_url is not configured")

        url = settings.openai_tts_url.rstrip("/") + "/v1/audio/speech"
        voice = _VOICE_MAP.get(language_code, _DEFAULT_VOICE)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.openai_tts_api_key:
            headers["Authorization"] = f"Bearer {settings.openai_tts_api_key}"

        payload = {
            "model": settings.openai_tts_model,
            "input": text,
            "voice": voice,
            "response_format": "mp3",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content

    async def list_models(self) -> list[str]:
        """Fetch available model ids from the upstream /v1/models endpoint.

        Returns an empty list if the server doesn't implement the endpoint or
        returns an unexpected shape.
        """
        settings = get_settings()
        if not settings.openai_tts_url:
            raise RuntimeError("openai_tts_url is not configured")

        url = settings.openai_tts_url.rstrip("/") + "/v1/models"
        headers: dict[str, str] = {}
        if settings.openai_tts_api_key:
            headers["Authorization"] = f"Bearer {settings.openai_tts_api_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        # OpenAI shape: {"object": "list", "data": [{"id": "...", ...}, ...]}
        entries = data.get("data") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            return []
        return [m["id"] for m in entries if isinstance(m, dict) and "id" in m]
