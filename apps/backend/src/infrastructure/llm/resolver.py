from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.infrastructure.db.repositories.provider_repo import ProviderRepository
from src.infrastructure.db.repositories.system_api_key_repo import SystemApiKeyRepository
from src.infrastructure.llm.client import LLMClient
from src.infrastructure.llm.openai_client import OpenAIClient

_provider_repo = ProviderRepository()
_system_key_repo = SystemApiKeyRepository()


async def resolve_llm_client(session: AsyncSession) -> LLMClient:
    """Return a ready-to-use OpenAI LLM client.

    Key resolution: system DB key → env var.
    Model resolution: system DB model → env var (`openai_model`).
    Raises HTTP 503 if no key is configured.
    """
    settings = get_settings()

    provider = await _provider_repo.find_by_slug(session, "openai")

    key: str | None = None
    model: str = settings.openai_model
    if provider:
        key = await _system_key_repo.get_decrypted(session, provider.id)
        db_model = await _system_key_repo.get_model(session, provider.id)
        if db_model:
            model = db_model
    if not key:
        key = settings.openai_api_key

    if key:
        return OpenAIClient(api_key=key, model=model)

    raise HTTPException(
        status_code=503,
        detail=(
            "No OpenAI API key configured. "
            "Set openai_api_key in environment variables "
            "or add a system API key via the admin panel."
        ),
    )
