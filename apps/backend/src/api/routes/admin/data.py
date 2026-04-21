import os
import shutil

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_redis, require_admin
from src.core import get_settings
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.activity_repo import DailyActivityRepository
from src.infrastructure.db.repositories.content_repo import ContentRepository
from src.infrastructure.db.repositories.word_repo import WordRepository

router = APIRouter(prefix="/admin/data", tags=["admin"])

_content_repo = ContentRepository()
_word_repo = WordRepository()
_activity_repo = DailyActivityRepository()

CONFIRMATION_PHRASE = "DELETE ALL DATA"


class DataResetRequest(BaseModel):
    confirmation: str


class DataResetResponse(BaseModel):
    deleted_books: int
    deleted_words: int


@router.delete("/activity", status_code=204)
async def reset_activity(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Wipe all daily activity rows for all users (streaks + page counts)."""
    await _activity_repo.delete_all(session)
    await session.commit()
    async for key in redis.scan_iter("stats:*"):
        await redis.delete(key)


@router.delete("/reset", response_model=DataResetResponse)
async def reset_all_data(
    body: DataResetRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> DataResetResponse:
    """Delete all books, pages, and vocabulary for all users. Irreversible."""
    if body.confirmation != CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=422,
            detail=f"Confirmation phrase must be exactly: {CONFIRMATION_PHRASE}",
        )

    deleted_words = await _word_repo.delete_all(session)
    deleted_books = await _content_repo.delete_all(session)

    await session.commit()

    # Flush stats cache for all users
    async for key in redis.scan_iter("stats:*"):
        await redis.delete(key)

    # Remove uploaded book files from disk
    settings = get_settings()
    books_dir = os.path.join(settings.storage_root, "books")
    if os.path.isdir(books_dir):
        shutil.rmtree(books_dir)
        os.makedirs(books_dir, exist_ok=True)

    return DataResetResponse(deleted_books=deleted_books, deleted_words=deleted_words)
