import os
import uuid

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.core.config import get_settings
from src.domain.auth.services.jwt import decode_token
from src.infrastructure.db.models.content import Book

from ._deps import content_service

router = APIRouter(prefix="/books", tags=["books"])


_COVER_MEDIA_TYPE_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


@router.get("/{book_id}/cover")
async def get_book_cover(
    book_id: uuid.UUID,
    request: Request,
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream a book's cover image.

    Accepts ``Bearer`` header or ``?token=`` query param — the latter is
    required by ``<img>`` tags, which can't set custom headers.
    """
    raw_token = token or ""
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[len("Bearer "):]

    user_id: uuid.UUID | None = None
    if raw_token:
        try:
            payload = decode_token(raw_token)
            if payload.get("type") == "access":
                user_id = uuid.UUID(payload["sub"])
        except (pyjwt.InvalidTokenError, ValueError):
            pass

    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != user_id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book or not book.cover_image_path:
        raise HTTPException(status_code=404, detail="No cover for this book")

    settings = get_settings()
    # Resolve symlinks before the prefix check to block directory traversal.
    abs_path = os.path.realpath(
        os.path.join(settings.storage_root, book.cover_image_path)
    )
    expected_prefix = os.path.realpath(
        os.path.join(settings.storage_root, "books", str(book_id))
    )
    if not abs_path.startswith(expected_prefix + os.sep):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="Cover not found on disk")

    ext = os.path.splitext(abs_path)[1].lower()
    media_type = _COVER_MEDIA_TYPE_BY_EXT.get(ext, "application/octet-stream")
    file_size = os.path.getsize(abs_path)

    def _iter_file(path: str, chunk_size: int = 65536):
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk

    return StreamingResponse(
        _iter_file(abs_path),
        media_type=media_type,
        headers={
            "Content-Length": str(file_size),
            "Cache-Control": "private, max-age=86400",
        },
    )


__all__ = ["router"]
