import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.deepl_instance_repo import DeepLInstanceRepository

router = APIRouter(prefix="/admin/deepl-instances", tags=["admin"])
_repo = DeepLInstanceRepository()

# DeepL-supported language codes (uppercase)
DEEPL_LANGUAGES = {
    "BG", "CS", "DA", "DE", "EL", "EN", "ES", "ET", "FI", "FR",
    "HU", "ID", "IT", "JA", "KO", "LT", "LV", "NB", "NL", "PL",
    "PT", "RO", "RU", "SK", "SL", "SV", "TR", "UK", "ZH",
}


class DeepLInstanceResponse(BaseModel):
    id: uuid.UUID
    source_lang: str
    target_lang: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateDeepLInstanceRequest(BaseModel):
    source_lang: str
    target_lang: str


class ToggleDeepLInstanceRequest(BaseModel):
    enabled: bool


@router.get("", response_model=list[DeepLInstanceResponse])
async def list_instances(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[DeepLInstanceResponse]:
    instances = await _repo.list_all(session)
    return [DeepLInstanceResponse.model_validate(i) for i in instances]


@router.post("", response_model=DeepLInstanceResponse, status_code=201)
async def create_instance(
    body: CreateDeepLInstanceRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> DeepLInstanceResponse:
    src = body.source_lang.upper()
    tgt = body.target_lang.upper()

    if src not in DEEPL_LANGUAGES:
        raise HTTPException(status_code=422, detail=f"Unsupported source language: {src}")
    if tgt not in DEEPL_LANGUAGES:
        raise HTTPException(status_code=422, detail=f"Unsupported target language: {tgt}")
    if src == tgt:
        raise HTTPException(status_code=422, detail="Source and target language must differ")

    instance = await _repo.create(session, src, tgt)
    await session.commit()
    await session.refresh(instance)
    return DeepLInstanceResponse.model_validate(instance)


@router.patch("/{instance_id}", response_model=DeepLInstanceResponse)
async def toggle_instance(
    instance_id: uuid.UUID,
    body: ToggleDeepLInstanceRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> DeepLInstanceResponse:
    instance = await _repo.toggle_enabled(session, instance_id, body.enabled)
    if instance is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    await session.commit()
    return DeepLInstanceResponse.model_validate(instance)


@router.delete("/{instance_id}", status_code=204)
async def delete_instance(
    instance_id: uuid.UUID,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    deleted = await _repo.delete(session, instance_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Instance not found")
    await session.commit()
