import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.sentences_repo import SavedSentenceRepository

router = APIRouter(prefix="/sentences", tags=["sentences"])
_repo = SavedSentenceRepository()


class SentenceToken(BaseModel):
    w: str
    pos: str = ""
    feats: str = ""
    dep_head: int = 0
    dep_rel: str = ""


class SaveSentenceRequest(BaseModel):
    language_id: int
    sentence_text: str
    sentence_index: int
    book_id: Optional[uuid.UUID] = None
    tokens: Optional[list[SentenceToken]] = None


class SavedSentenceResponse(BaseModel):
    id: uuid.UUID
    language_id: int
    sentence_text: str
    sentence_index: int
    book_id: Optional[uuid.UUID]
    tokens: Optional[list[SentenceToken]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=SavedSentenceResponse, status_code=201)
async def save_sentence(
    body: SaveSentenceRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SavedSentenceResponse:
    tokens_json = [t.model_dump() for t in body.tokens] if body.tokens else None
    try:
        sentence = await _repo.create(
            session,
            user_id=current_user.id,
            language_id=body.language_id,
            sentence_text=body.sentence_text,
            sentence_index=body.sentence_index,
            book_id=body.book_id,
            tokens=tokens_json,
        )
        await session.commit()
        return SavedSentenceResponse.model_validate(sentence)
    except IntegrityError:
        # The unique constraint on (user_id, book_id, sentence_index) fired —
        # user has already saved this sentence.
        await session.rollback()
        raise HTTPException(status_code=409, detail="Sentence already saved")


@router.get("", response_model=list[SavedSentenceResponse])
async def list_sentences(
    language_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[SavedSentenceResponse]:
    sentences = await _repo.list_by_language(
        session, user_id=current_user.id, language_id=language_id
    )
    return [SavedSentenceResponse.model_validate(s) for s in sentences]


@router.delete("/{sentence_id}", status_code=204)
async def delete_sentence(
    sentence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    sentence = await _repo.find_by_id(session, sentence_id)
    if not sentence or sentence.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sentence not found")
    await _repo.delete(session, sentence_id)
    await session.commit()
