from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.infrastructure.db.repositories.provider_repo import ProviderRepository
from src.infrastructure.db.repositories.system_api_key_repo import SystemApiKeyRepository
from src.infrastructure.llm.claude_client import ClaudeClient
from src.infrastructure.llm.client import LLMClient
from src.infrastructure.llm.openai_client import OpenAIClient

_provider_repo = ProviderRepository()
_system_key_repo = SystemApiKeyRepository()


async def resolve_llm_client(session: AsyncSession) -> LLMClient:
    """Return a ready-to-use LLM client.

    Cascade: system DB key → env var. Tries OpenAI first, then Claude.
    Raises HTTP 503 if no provider is configured.
    """
    settings = get_settings()

    for slug, env_key, env_model, make_client in [
        (
            "openai",
            settings.openai_api_key,
            settings.openai_model,
            lambda key, model: OpenAIClient(api_key=key, model=model),
        ),
        (
            "claude",
            settings.claude_api_key,
            settings.claude_model,
            lambda key, model: ClaudeClient(api_key=key, model=model),
        ),
    ]:
        provider = await _provider_repo.find_by_slug(session, slug)

        key: str | None = None
        model: str = env_model
        if provider:
            key = await _system_key_repo.get_decrypted(session, provider.id)
            db_model = await _system_key_repo.get_model(session, provider.id)
            if db_model:
                model = db_model
        if not key:
            key = env_key

        if key:
            return make_client(key, model)  # type: ignore[operator]

    raise HTTPException(
        status_code=503,
        detail=(
            "No LLM provider configured. "
            "Set openai_api_key or claude_api_key in environment variables, "
            "or add a system API key via the admin panel."
        ),
    )
