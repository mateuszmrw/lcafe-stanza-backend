from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.core.config import get_settings
from src.infrastructure.db.models.users import User
from src.infrastructure.tts.providers.qwen import SUPPORTED_LANGUAGES

router = APIRouter(prefix="/admin/tts", tags=["admin"])


class TtsProviderStatus(BaseModel):
    provider_slug: str
    supported_languages: list[str]
    url_configured: bool
    key_configured: bool
    url: str | None  # shown to admins for transparency


class TtsProviderUpdateRequest(BaseModel):
    url: str | None = None
    api_key: str | None = None


@router.get("", response_model=list[TtsProviderStatus])
async def list_tts_providers(
    _: User = Depends(require_admin),
    __: AsyncSession = Depends(get_db),
) -> list[TtsProviderStatus]:
    """List TTS provider configuration status."""
    settings = get_settings()
    return [
        TtsProviderStatus(
            provider_slug="qwen",
            supported_languages=sorted(SUPPORTED_LANGUAGES),
            url_configured=bool(settings.qwen_tts_url),
            key_configured=bool(settings.qwen_tts_api_key),
            url=settings.qwen_tts_url,
        )
    ]


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
    if provider_slug != "qwen":
        raise HTTPException(status_code=404, detail="Unknown TTS provider")
    # Settings are env-var backed and immutable at runtime.
    # This endpoint exists so the admin UI can document expected env vars.
    raise HTTPException(
        status_code=400,
        detail=(
            "TTS settings are configured via environment variables. "
            "Set qwen_tts_url to your mlx-audio server (e.g. http://localhost:8000). "
            "Start it with: python -m mlx_audio.server --host 0.0.0.0 --port 8000"
        ),
    )
