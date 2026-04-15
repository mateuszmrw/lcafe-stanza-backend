import logging

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.api.schemas.grammar import GrammarExplainRequest, GrammarExplainResponse
from src.core.config import get_settings
from src.domain.grammar.service import GrammarExplanationService
from src.infrastructure.db.models.users import User, UserLanguageProfile
from src.infrastructure.db.repositories.provider_repo import ProviderRepository
from src.infrastructure.db.repositories.system_api_key_repo import SystemApiKeyRepository
from src.infrastructure.llm.claude_client import ClaudeClient
from src.infrastructure.llm.client import LLMClient
from src.infrastructure.llm.openai_client import OpenAIClient

log = logging.getLogger(__name__)

router = APIRouter(prefix="/grammar", tags=["grammar"])
_provider_repo = ProviderRepository()
_system_key_repo = SystemApiKeyRepository()

_RATE_LIMIT = 3
_RATE_WINDOW = 60  # seconds


async def _resolve_llm_client(session: AsyncSession) -> LLMClient:
    """Resolve an LLM client using admin-configured keys only.
    Cascade: system DB key → env var. Tries OpenAI first, then Claude."""
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
            "or add a system API key for the 'openai' or 'claude' provider."
        ),
    )


async def _check_rate_limit(redis: Redis, user_id: str) -> None:
    key = f"grammar:user:{user_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _RATE_WINDOW)
    if count > _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {_RATE_LIMIT} grammar requests per minute.",
        )


@router.post("/explain", response_model=GrammarExplainResponse)
async def explain_grammar(
    body: GrammarExplainRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> GrammarExplainResponse:
    if not body.tokens:
        raise HTTPException(status_code=422, detail="tokens must not be empty")

    lang_profile = None
    if current_user.active_language_id is not None:
        result = await session.execute(
            sa.select(UserLanguageProfile).where(
                UserLanguageProfile.user_id == current_user.id,
                UserLanguageProfile.language_id == current_user.active_language_id,
            )
        )
        lang_profile = result.scalar_one_or_none()

    if not lang_profile or not lang_profile.proficiency_level:
        raise HTTPException(
            status_code=400,
            detail="Please set your proficiency level first (PATCH /users/me/proficiency).",
        )

    await _check_rate_limit(redis, str(current_user.id))

    llm = await _resolve_llm_client(session)
    service = GrammarExplanationService(llm)

    try:
        return await service.explain(
            tokens=body.tokens,
            language_code=body.language_code,
            proficiency_level=lang_profile.proficiency_level,
            native_language_code=current_user.native_language_code or "en",
            register=body.register,
        )
    except ValueError as exc:
        log.error("Grammar explanation failed: %s", exc)
        raise HTTPException(status_code=502, detail="LLM returned an invalid response. Try again.")
