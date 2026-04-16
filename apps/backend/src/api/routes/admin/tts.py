import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.core.config import get_settings
from src.infrastructure.db.models.users import User
from src.infrastructure.tts.providers.openai_tts import (
    SUPPORTED_LANGUAGES,
    OpenAITtsProvider,
)

router = APIRouter(prefix="/admin/tts", tags=["admin"])

_PROVIDER_SLUG = "openai-tts"


class TtsProviderStatus(BaseModel):
    provider_slug: str
    supported_languages: list[str]
    url_configured: bool
    key_configured: bool
    url: str | None  # shown to admins for transparency
    model: str


class TtsProviderUpdateRequest(BaseModel):
    url: str | None = None
    api_key: str | None = None


class TtsModelsResponse(BaseModel):
    models: list[str]


@router.get("", response_model=list[TtsProviderStatus])
async def list_tts_providers(
    _: User = Depends(require_admin),
    __: AsyncSession = Depends(get_db),
) -> list[TtsProviderStatus]:
    """List TTS provider configuration status."""
    settings = get_settings()
    return [
        TtsProviderStatus(
            provider_slug=_PROVIDER_SLUG,
            supported_languages=sorted(SUPPORTED_LANGUAGES),
            url_configured=bool(settings.openai_tts_url),
            key_configured=bool(settings.openai_tts_api_key),
            url=settings.openai_tts_url,
            model=settings.openai_tts_model,
        )
    ]


@router.get("/models", response_model=TtsModelsResponse)
async def list_tts_models(
    _: User = Depends(require_admin),
) -> TtsModelsResponse:
    """Fetch available TTS models from the configured upstream server."""
    settings = get_settings()
    if not settings.openai_tts_url:
        raise HTTPException(
            status_code=400,
            detail="openai_tts_url is not configured",
        )
    try:
        models = await OpenAITtsProvider().list_models()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch models from upstream: {exc}",
        ) from exc
    return TtsModelsResponse(models=models)


@router.put("/{provider_slug}", status_code=204)
async def update_tts_provider(
    provider_slug: str,
    body: TtsProviderUpdateRequest,
    _: User = Depends(require_admin),
    __: AsyncSession = Depends(get_db),
) -> None:
    """Update TTS provider URL / API key.

    Note: these values are read from environment variables at startup.
    Use this endpoint to confirm current configuration; to change them,
    update the environment and restart the backend.
    """
    if provider_slug != _PROVIDER_SLUG:
        raise HTTPException(status_code=404, detail="Unknown TTS provider")
    # Settings are env-var backed and immutable at runtime.
    # This endpoint exists so the admin UI can document expected env vars.
    raise HTTPException(
        status_code=400,
        detail=(
            "TTS settings are configured via environment variables. "
            "Set OPENAI_TTS_URL, OPENAI_TTS_API_KEY, and OPENAI_TTS_MODEL "
            "for an OpenAI-compatible audio server."
        ),
    )
