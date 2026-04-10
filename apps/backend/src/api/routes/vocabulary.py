import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas.vocabulary import VocabularyStatusUpdate, VocabularyUpsertRequest, WordListResponse, WordResponse
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.word_repo import WordRepository

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])
_word_repo = WordRepository()


@router.get("", response_model=WordListResponse)
async def list_vocabulary(
    language_id: int,
    status: str | None = None,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WordListResponse:
    words, total = await _word_repo.list_paginated(
        session,
        user_id=current_user.id,
        language_id=language_id,
        status=status,
        page=page,
        limit=limit,
    )
    return WordListResponse(
        items=[WordResponse.model_validate(w) for w in words],
        total=total,
        page=page,
        limit=limit,
    )


@router.put("", response_model=WordResponse)
async def upsert_word_status(
    body: VocabularyUpsertRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WordResponse:
    """Create a vocabulary entry if it doesn't exist, then set its status."""
    word = await _word_repo.upsert_with_status(
        session,
        user_id=current_user.id,
        language_id=body.language_id,
        word=body.word,
        status=body.status,
        lemma=body.lemma,
        pos=body.pos,
        reading=body.reading,
        gender=body.gender,
        feats=body.feats,
    )
    await session.commit()
    return WordResponse.model_validate(word)


@router.post("/batch", status_code=204)
async def batch_upsert_word_status(
    body: list[VocabularyUpsertRequest],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Upsert status for multiple words in one request (e.g. auto-advance on page turn)."""
    rows = [
        {
            "user_id": current_user.id,
            "language_id": item.language_id,
            "word": item.word.lower().strip(),
            "status": item.status,
            "lemma": item.lemma,
            "pos": item.pos,
            "reading": item.reading,
            "gender": item.gender,
            "feats": item.feats,
        }
        for item in body
    ]
    await _word_repo.batch_upsert_status(session, rows)
    await session.commit()


@router.get("/{word_id}", response_model=WordResponse)
async def get_word(
    word_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WordResponse:
    word = await _word_repo.find_by_id(session, word_id)
    if not word or word.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Word not found")
    return WordResponse.model_validate(word)


@router.patch("/{word_id}/status", response_model=WordResponse)
async def update_word_status(
    word_id: uuid.UUID,
    body: VocabularyStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WordResponse:
    word = await _word_repo.find_by_id(session, word_id)
    if not word or word.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Word not found")

    updated = await _word_repo.update_status(session, word_id, body.status)
    await session.commit()
    return WordResponse.model_validate(updated)
