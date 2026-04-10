from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.api.schemas.admin import ProviderResponse
from src.core.config import get_settings
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.provider_repo import ProviderRepository
from src.infrastructure.db.repositories.system_api_key_repo import SystemApiKeyRepository

router = APIRouter(prefix="/admin/system/api-keys", tags=["admin"])
_provider_repo = ProviderRepository()
_system_key_repo = SystemApiKeyRepository()


class SystemApiKeyStatus(BaseModel):
    provider_slug: str
    provider: ProviderResponse
    exists: bool
    source: str  # "database" | "env" | "none"


class SystemApiKeyUpsertRequest(BaseModel):
    api_key: str


@router.get("", response_model=list[SystemApiKeyStatus])
async def list_system_keys(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[SystemApiKeyStatus]:
    """List all translation providers and their system-level key status."""
    providers = await _provider_repo.list_active_by_type(session, "translation")
    result: list[SystemApiKeyStatus] = []

    for provider in providers:
        db_exists = await _system_key_repo.exists(session, provider.id)
        # Determine source
        if db_exists:
            source = "database"
        elif provider.slug == "deepl" and get_settings().deepl_api_key:
            source = "env"
        else:
            source = "none"

        result.append(SystemApiKeyStatus(
            provider_slug=provider.slug,
            provider=ProviderResponse.model_validate(provider),
            exists=source != "none",
            source=source,
        ))

    return result


@router.put("/{provider_slug}", status_code=204)
async def set_system_key(
    provider_slug: str,
    body: SystemApiKeyUpsertRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Set or update the system-level API key for a provider."""
    provider = await _provider_repo.find_by_slug(session, provider_slug, type_filter="translation")
    if not provider:
        raise HTTPException(status_code=404, detail="Translation provider not found")

    await _system_key_repo.upsert(session, provider.id, body.api_key.strip())
    await session.commit()


@router.delete("/{provider_slug}", status_code=204)
async def delete_system_key(
    provider_slug: str,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove the system-level API key for a provider."""
    provider = await _provider_repo.find_by_slug(session, provider_slug, type_filter="translation")
    if not provider:
        raise HTTPException(status_code=404, detail="Translation provider not found")

    await _system_key_repo.delete(session, provider.id)
    await session.commit()
