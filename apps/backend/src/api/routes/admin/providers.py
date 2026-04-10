import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.api.schemas.admin import ProviderPatchRequest, ProviderResponse
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.provider_repo import ProviderRepository

router = APIRouter(prefix="/admin/providers", tags=["admin"])
_provider_repo = ProviderRepository()


@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    type: str | None = None,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[ProviderResponse]:
    providers = await _provider_repo.list_all(session, type_filter=type)
    return [ProviderResponse.model_validate(p) for p in providers]


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    body: ProviderPatchRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> ProviderResponse:
    provider = await _provider_repo.update(
        session,
        provider_id,
        name=body.name,
        description=body.description,
        is_active=body.is_active,
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await session.commit()
    return ProviderResponse.model_validate(provider)
