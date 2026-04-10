import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas.admin import ProviderResponse
from src.core.config import get_settings
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.api_key_repo import ApiKeyRepository
from src.infrastructure.db.repositories.deepl_instance_repo import DeepLInstanceRepository
from src.infrastructure.db.repositories.provider_repo import ProviderRepository
from src.infrastructure.db.repositories.system_api_key_repo import SystemApiKeyRepository
from src.infrastructure.deepl.client import DeepLClient

log = logging.getLogger(__name__)

router = APIRouter(prefix="/translate", tags=["translation"])
_provider_repo = ProviderRepository()
_api_key_repo = ApiKeyRepository()
_system_key_repo = SystemApiKeyRepository()
_instance_repo = DeepLInstanceRepository()


async def _resolve_api_key(
    session: AsyncSession, user: User, provider_id: object, provider_slug: str
) -> str | None:
    """Cascade: user key → system DB key → env var → None."""
    import uuid as _uuid
    pid = provider_id if isinstance(provider_id, _uuid.UUID) else _uuid.UUID(str(provider_id))

    key = await _api_key_repo.get_decrypted(session, user.id, pid)
    if key:
        return key

    key = await _system_key_repo.get_decrypted(session, pid)
    if key:
        return key

    if provider_slug == "deepl":
        return get_settings().deepl_api_key or None

    return None


class TranslationAvailabilityResponse(BaseModel):
    available: bool
    providers: list[ProviderResponse]


class TranslationResult(BaseModel):
    provider_slug: str
    target_lang: str
    translated_texts: list[str]


class TranslationResponse(BaseModel):
    results: list[TranslationResult]


class TranslateRequest(BaseModel):
    text: str
    source_lang: str


@router.get("/available", response_model=TranslationAvailabilityResponse)
async def translation_available(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TranslationAvailabilityResponse:
    """Return which translation providers are available for this user."""
    providers = await _provider_repo.list_active_by_type(session, "translation")
    available: list[ProviderResponse] = []

    for provider in providers:
        key = await _resolve_api_key(session, current_user, provider.id, provider.slug)
        if key is not None:
            available.append(ProviderResponse.model_validate(provider))

    return TranslationAvailabilityResponse(
        available=len(available) > 0,
        providers=available,
    )


@router.post("", response_model=TranslationResponse)
async def translate(
    body: TranslateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TranslationResponse:
    providers = await _provider_repo.list_active_by_type(session, "translation")

    # Find the DeepL provider and resolve its key once
    deepl_provider = next((p for p in providers if p.slug == "deepl"), None)
    deepl_key: str | None = None
    if deepl_provider:
        deepl_key = await _resolve_api_key(
            session, current_user, deepl_provider.id, "deepl"
        )

    if deepl_key is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "No translation provider configured. "
                "Set your DeepL API key on the admin system-keys page "
                "or via the DEEPL_API_KEY env var."
            ),
        )

    # Load enabled DeepL instances for this source language
    instances = await _instance_repo.list_enabled_for_source(session, body.source_lang)

    if not instances:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No DeepL instances configured for source language '{body.source_lang}'. "
                "Add one on the admin DeepL instances page."
            ),
        )

    async def _translate_to(target_lang: str) -> TranslationResult | None:
        try:
            client = DeepLClient(api_key=deepl_key)  # type: ignore[arg-type]
            texts = await client.translate(body.text, body.source_lang, target_lang)
            if not texts:
                return None
            return TranslationResult(
                provider_slug="deepl",
                target_lang=target_lang,
                translated_texts=texts,
            )
        except Exception as exc:
            log.warning("DeepL translation to %s failed: %s", target_lang, exc)
            return None

    results_raw = await asyncio.gather(*[_translate_to(i.target_lang) for i in instances])
    results = [r for r in results_raw if r is not None]

    if not results:
        raise HTTPException(
            status_code=503,
            detail="DeepL returned no results. Check that the API key is valid.",
        )

    return TranslationResponse(results=results)
