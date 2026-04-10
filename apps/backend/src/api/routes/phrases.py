import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas.phrases import PhraseCreate, PhraseListResponse, PhraseResponse, PhraseUpdate
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.phrase_repo import PhraseRepository

router = APIRouter(prefix="/phrases", tags=["phrases"])
_phrase_repo = PhraseRepository()

VALID_STATUSES = {"learning", "known"}


@router.post("", response_model=PhraseResponse, status_code=201)
async def create_phrase(
    body: PhraseCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PhraseResponse:
    phrase = await _phrase_repo.create(
        session,
        user_id=current_user.id,
        language_id=body.language_id,
        text=body.text,
        translation=body.translation,
        context=body.context,
        book_id=body.book_id,
        page=body.page,
    )
    await session.commit()
    return PhraseResponse.model_validate(phrase)


@router.get("", response_model=PhraseListResponse)
async def list_phrases(
    language_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PhraseListResponse:
    phrases, total = await _phrase_repo.list_paginated(
        session,
        user_id=current_user.id,
        language_id=language_id,
        status=status,
        page=page,
        limit=limit,
    )
    return PhraseListResponse(
        items=[PhraseResponse.model_validate(p) for p in phrases],
        total=total,
        page=page,
        limit=limit,
    )


@router.patch("/{phrase_id}", response_model=PhraseResponse)
async def update_phrase_status(
    phrase_id: uuid.UUID,
    body: PhraseUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PhraseResponse:
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(VALID_STATUSES)}")
    phrase = await _phrase_repo.update_status(session, phrase_id, current_user.id, body.status)
    if not phrase:
        raise HTTPException(status_code=404, detail="Phrase not found")
    await session.commit()
    return PhraseResponse.model_validate(phrase)


@router.delete("/{phrase_id}", status_code=204)
async def delete_phrase(
    phrase_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    deleted = await _phrase_repo.delete(session, phrase_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Phrase not found")
    await session.commit()
