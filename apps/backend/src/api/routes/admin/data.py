import os
import shutil

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.core import get_settings
from src.infrastructure.db.models.content import ContentItem
from src.infrastructure.db.models.users import User
from src.infrastructure.db.models.words import Word

router = APIRouter(prefix="/admin/data", tags=["admin"])

CONFIRMATION_PHRASE = "DELETE ALL DATA"


class DataResetRequest(BaseModel):
    confirmation: str


class DataResetResponse(BaseModel):
    deleted_books: int
    deleted_words: int


@router.delete("/reset", response_model=DataResetResponse)
async def reset_all_data(
    body: DataResetRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> DataResetResponse:
    """Delete all books, pages, and vocabulary for all users. Irreversible."""
    if body.confirmation != CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=422,
            detail=f"Confirmation phrase must be exactly: {CONFIRMATION_PHRASE}",
        )

    words_result = await session.execute(sa.delete(Word))
    deleted_words = words_result.rowcount

    books_result = await session.execute(sa.delete(ContentItem))
    deleted_books = books_result.rowcount

    await session.commit()

    # Remove uploaded book files from disk
    settings = get_settings()
    books_dir = os.path.join(settings.storage_root, "books")
    if os.path.isdir(books_dir):
        shutil.rmtree(books_dir)
        os.makedirs(books_dir, exist_ok=True)

    return DataResetResponse(deleted_books=deleted_books, deleted_words=deleted_words)
