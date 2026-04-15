from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.anki_repo import AnkiRepository

router = APIRouter(prefix="/admin/anki", tags=["admin"])
_repo = AnkiRepository()


class AnkiSettingsResponse(BaseModel):
    anki_connect_url: Optional[str]
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateAnkiSettingsRequest(BaseModel):
    anki_connect_url: Optional[str] = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


@router.get("/settings", response_model=AnkiSettingsResponse)
async def get_settings(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> AnkiSettingsResponse:
    settings = await _repo.get_settings(session)
    await session.commit()
    return AnkiSettingsResponse.model_validate(settings)


@router.patch("/settings", response_model=AnkiSettingsResponse)
async def update_settings(
    body: UpdateAnkiSettingsRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> AnkiSettingsResponse:
    settings = await _repo.update_url(session, body.anki_connect_url)
    await session.commit()
    return AnkiSettingsResponse.model_validate(settings)


@router.post("/test", response_model=TestConnectionResponse)
async def test_connection(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> TestConnectionResponse:
    settings = await _repo.get_settings(session)
    if not settings.anki_connect_url:
        return TestConnectionResponse(
            success=False, message="No AnkiConnect URL configured"
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                settings.anki_connect_url,
                json={"action": "version", "version": 6},
            )
            resp.raise_for_status()
            data = resp.json()
            version = data.get("result", "unknown")
            return TestConnectionResponse(
                success=True, message=f"Connected — AnkiConnect v{version}"
            )
    except Exception as exc:
        return TestConnectionResponse(success=False, message=str(exc))
