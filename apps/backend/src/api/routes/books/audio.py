import json
import os
import shutil
import uuid
from typing import AsyncGenerator

import jwt as pyjwt
from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import get_arq_pool, get_current_user, get_db, get_redis
from src.domain.content.import_service import AUDIO_ALIGN_CHANNEL
from src.api.schemas.audio import (
    AudioStatusResponse,
    SentenceAlignmentResponse,
    TimeIndexEntry,
    TimeIndexResponse,
)
from src.core.config import get_settings
from src.domain.auth.services.jwt import decode_token
from src.infrastructure.db.models.content import Book
from src.infrastructure.db.models.users import User

from ._deps import audio_repo, content_service, page_repo

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/{book_id}/audio/status", response_model=AudioStatusResponse)
async def get_audio_status(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AudioStatusResponse:
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    sentences_aligned = await audio_repo.count_alignments_for_book(session, book_id)

    return AudioStatusResponse(
        has_audio_overlay=book.has_audio_overlay,
        audio_overlay_status=book.audio_overlay_status,
        audio_duration_ms=book.audio_duration_ms,
        sentences_aligned=sentences_aligned,
    )


@router.get("/{book_id}/audio/status/stream")
async def stream_audio_status(
    book_id: uuid.UUID,
    request: Request,
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> EventSourceResponse:
    """SSE stream for audio alignment progress. Accepts ?token= since EventSource cannot set headers."""
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

    book = await session.get(Book, book_id)
    overlay_status = book.audio_overlay_status if book else None

    async def event_generator() -> AsyncGenerator[dict, None]:
        if overlay_status in ("complete", "failed"):
            event = "complete" if overlay_status == "complete" else "failed"
            yield {"data": json.dumps({"event": event, "data": {}})}
            return

        channel = AUDIO_ALIGN_CHANNEL.format(book_id=book_id)
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    payload = json.loads(message["data"])
                    yield {"data": json.dumps(payload)}
                    if payload.get("event") in ("complete", "failed"):
                        break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return EventSourceResponse(event_generator())


@router.get("/{book_id}/audio/stream")
async def stream_audio(
    book_id: uuid.UUID,
    request: Request,
    token: str | None = Query(
        default=None,
        description="JWT token (for <audio> elements that cannot set headers)",
    ),
    file_path: str | None = Query(
        default=None, description="Storage-relative path to a specific audio file"
    ),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream audio file.

    Accepts Bearer Authorization header or ?token= query param.
    For SMIL books with multiple audio files, pass ?file_path= (from alignment response).
    Falls back to book.audio_file_path when file_path is not given.
    """
    current_user: User | None = None

    raw_token = token
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[len("Bearer "):]

    if raw_token:
        try:
            payload = decode_token(raw_token)
            if payload.get("type") == "access":
                user_id_str = payload.get("sub")
                if user_id_str:
                    current_user = await session.get(User, uuid.UUID(user_id_str))
        except (pyjwt.InvalidTokenError, ValueError):
            pass

    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not current_user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")

    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    settings = get_settings()

    if file_path:
        # realpath resolves symlinks before the prefix check — normpath alone
        # does not, which would allow traversal via symlink.
        abs_path = os.path.realpath(os.path.join(settings.storage_root, file_path))
        expected_prefix = os.path.realpath(
            os.path.join(settings.storage_root, "books", str(book_id), "audio")
        )
        if not abs_path.startswith(expected_prefix + os.sep):
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        if not book.audio_file_path:
            raise HTTPException(status_code=404, detail="No audio file for this book")
        abs_path = os.path.join(settings.storage_root, book.audio_file_path)

    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    ext = os.path.splitext(abs_path)[1].lower()
    media_type_map = {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".wav": "audio/wav",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
    }
    media_type = media_type_map.get(ext, "application/octet-stream")

    def _iter_file(path: str, chunk_size: int = 65536):
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk

    file_size = os.path.getsize(abs_path)
    return StreamingResponse(
        _iter_file(abs_path),
        media_type=media_type,
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="audio{ext}"',
        },
    )


@router.post("/{book_id}/audio/realign-smil", status_code=202)
async def realign_smil_audio(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> dict:
    """Re-run SMIL alignment for an existing book without re-importing pages.

    Clears existing sentence alignments (extracted audio files on disk are
    re-used) and re-enqueues the align_smil_audio worker task. Use this after
    fixing alignment logic / debugging unresolved fragments.
    """
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book or not book.has_audio_overlay:
        raise HTTPException(
            status_code=404, detail="Book has no SMIL audio overlay to realign"
        )

    if book.audio_overlay_status in ("pending", "in_progress"):
        raise HTTPException(
            status_code=409, detail="SMIL alignment already in progress"
        )

    # Drop existing alignments so the re-run inserts fresh rows. Audio files
    # on disk are kept — the extractor is idempotent and will re-use them.
    await audio_repo.delete_alignments_for_book(session, book_id)

    book.audio_overlay_status = "pending"
    await session.commit()

    await arq_pool.enqueue_job("align_smil_audio", str(book_id))
    return {"status": "queued"}


@router.delete("/{book_id}/audio", status_code=204)
async def delete_audio(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete extracted SMIL audio files and all sentence alignments for this book."""
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book or not book.has_audio_overlay:
        raise HTTPException(status_code=404, detail="No audio attached to this book")

    settings = get_settings()
    audio_dir = os.path.join(settings.storage_root, "books", str(book_id), "audio")
    if os.path.isdir(audio_dir):
        try:
            shutil.rmtree(audio_dir)
        except OSError:
            pass

    await audio_repo.delete_alignments_for_book(session, book_id)

    book.audio_file_path = None
    book.audio_duration_ms = None
    book.has_audio_overlay = False
    book.audio_overlay_status = "none"
    await session.commit()


@router.get(
    "/{book_id}/pages/{page_number}/alignments",
    response_model=list[SentenceAlignmentResponse],
)
async def get_page_alignments(
    book_id: uuid.UUID,
    page_number: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[SentenceAlignmentResponse]:
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    page = await page_repo.get_by_book_and_page_number(session, book_id, page_number)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    alignments = await audio_repo.get_alignments_for_page(session, page.id)
    return [SentenceAlignmentResponse(**a) for a in alignments]


@router.get("/{book_id}/time-index", response_model=TimeIndexResponse)
async def get_time_index(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TimeIndexResponse:
    """Return a flat sorted array of all sentence alignments for a book.

    Binary search on start_ms gives O(log N) page + sentence lookup per
    playback tick (powers video-synced reading).
    """
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    rows = await audio_repo.get_time_index(session, book_id)
    return TimeIndexResponse(index=[TimeIndexEntry(**r) for r in rows])


__all__ = ["router"]
