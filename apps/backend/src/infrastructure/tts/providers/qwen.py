"""QwenTtsProvider — call local mlx-audio Qwen3-TTS via OpenAI-compatible API.

Start the server with:
    pip install mlx-audio
    python -m mlx_audio.server --host 0.0.0.0 --port 8000

Set env: qwen_tts_url=http://localhost:8000
"""

from __future__ import annotations

import logging

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Languages supported by Qwen3-TTS CustomVoice
SUPPORTED_LANGUAGES = frozenset({"zh", "ko", "ru"})

# Default voice per language — Qwen3-TTS CustomVoice preset names.
# Override in settings if vllm-mlx serves different voice names.
_VOICE_MAP: dict[str, str] = {
    "zh": "Chelsie",
    "ko": "Cove",
    "ru": "Serena",
}
_DEFAULT_VOICE = "Serena"


class QwenTtsProvider:
    def supports(self, language_code: str) -> bool:
        return language_code in SUPPORTED_LANGUAGES

    async def generate(self, text: str, language_code: str) -> bytes:
        """Generate speech audio. Returns raw MP3 bytes."""
        settings = get_settings()
        if not settings.qwen_tts_url:
            raise RuntimeError("qwen_tts_url is not configured")

        url = settings.qwen_tts_url.rstrip("/") + "/v1/audio/speech"
        voice = _VOICE_MAP.get(language_code, _DEFAULT_VOICE)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.qwen_tts_api_key:
            headers["Authorization"] = f"Bearer {settings.qwen_tts_api_key}"

        payload = {
            "model": "qwen3-tts",
            "input": text,
            "voice": voice,
            "response_format": "mp3",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
