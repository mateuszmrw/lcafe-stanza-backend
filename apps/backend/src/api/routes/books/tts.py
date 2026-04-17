import os
import uuid

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_arq_pool, get_current_user, get_db
from src.api.schemas.audio import TtsStatusResponse
from src.core.config import get_settings
from src.domain.auth.services.jwt import decode_token
from src.infrastructure.db.models.content import Book
from src.infrastructure.db.models.users import User

from ._deps import content_service, page_repo

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/{book_id}/audio/generate-tts", status_code=202)
async def generate_tts(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> dict:
    """Dispatch TTS generation for a book that has no embedded audio."""
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    if content_item.status != "completed":
        raise HTTPException(status_code=409, detail="Book is not yet fully tokenized")

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.tts_status in ("in_progress", "pending"):
        raise HTTPException(
            status_code=409, detail="TTS generation already in progress"
        )

    book.tts_status = "pending"
    await session.commit()

    await arq_pool.enqueue_job("generate_tts_audio", str(book_id))
    return {"status": "queued"}


@router.get("/{book_id}/audio/tts-status", response_model=TtsStatusResponse)
async def get_tts_status(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TtsStatusResponse:
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    pages_total = await page_repo.count_by_book(session, book_id)
    pages_ready = await page_repo.count_tts_ready(session, book_id)

    return TtsStatusResponse(
        tts_status=book.tts_status,
        pages_total=pages_total,
        pages_ready=pages_ready,
    )


@router.get("/{book_id}/tts/{page_number}/{filename:path}")
async def serve_tts_file(
    book_id: uuid.UUID,
    page_number: int,
    filename: str,
    request: Request,
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Serve DASH manifest and segment files for TTS audio.

    Accepts ?token= since dash.js segment requests cannot set Authorization headers directly.
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
        except Exception:
            pass

    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != user_id:
        raise HTTPException(status_code=404, detail="Book not found")

    settings = get_settings()

    # Defense in depth: reject bad filenames before building the path. realpath
    # below would also catch it, but early rejection gives a clearer error.
    if "/" in filename or "\\" in filename or filename in ("", ".", "..") or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    rel_path = os.path.join("books", str(book_id), "tts", str(page_number), filename)
    abs_path = os.path.realpath(os.path.join(settings.storage_root, rel_path))
    expected_prefix = os.path.realpath(
        os.path.join(settings.storage_root, "books", str(book_id), "tts")
    )
    if not abs_path.startswith(expected_prefix + os.sep):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(filename)[1].lower()
    content_type_map = {
        ".mpd": "application/dash+xml",
        ".mp4": "video/mp4",
        ".m4s": "video/iso.segment",
        ".m4a": "audio/mp4",
    }
    content_type = content_type_map.get(ext, "application/octet-stream")

    file_size = os.path.getsize(abs_path)

    def iter_file():
        with open(abs_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        iter_file(),
        media_type=content_type,
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=3600",
        },
    )


__all__ = ["router"]
