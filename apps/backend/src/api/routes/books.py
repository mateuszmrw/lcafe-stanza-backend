import hashlib
import io
import json
import os
import uuid
import zipfile
from typing import AsyncGenerator

from arq import ArqRedis
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from fastapi import Query, Request
from src.api.dependencies import get_arq_pool, get_current_user, get_db, get_redis
from src.domain.auth.services.jwt import decode_token
from src.api.schemas.audio import AudioStatusResponse, SentenceAlignmentResponse, TtsStatusResponse
from src.api.schemas.books import (
    BookDetailResponse,
    BookListItem,
    BookListResponse,
    BookUploadResponse,
    ChapterSummary,
    PageListResponse,
    PageResponse,
    TokenWithStatus,
)
from src.core.config import get_settings
from src.domain.content.page_enricher import collect_surface_forms, enrich_page_tokens
from src.domain.content.service import ContentService
from src.domain.nlp.services.book_chunker import BookChunker
from src.domain.nlp.services.book_parser import BookParser
from src.domain.nlp.services.pdf_parser import PdfParser
from src.infrastructure.db.models.content import Book, ContentPage
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.audio_repo import AudioRepository
from src.infrastructure.db.repositories.content_page_repo import ContentPageRepository
from src.infrastructure.db.repositories.word_repo import WordRepository

router = APIRouter(prefix="/books", tags=["books"])
_content_service = ContentService()
_page_repo = ContentPageRepository()
_word_repo = WordRepository()
_audio_repo = AudioRepository()


@router.post("", response_model=BookUploadResponse, status_code=201)
async def upload_book(
    language_id: int = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    register: str | None = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
    redis: Redis = Depends(get_redis),
) -> BookUploadResponse:
    if current_user.active_language_id is None:
        raise HTTPException(status_code=400, detail="Set an active language before importing books")
    if language_id != current_user.active_language_id:
        raise HTTPException(status_code=400, detail="Book language must match your active language")

    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )

    # Detect format by magic bytes.
    _PDF_MAGIC = b"%PDF"
    is_pdf = content[:4] == _PDF_MAGIC

    if is_pdf:
        file_extension = "pdf"
    else:
        # Validate EPUB structure (case-insensitive — some EPUBs produced on macOS
        # use lower-case "meta-inf/container.xml").
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                names_lower = {n.lower() for n in zf.namelist()}
                if "meta-inf/container.xml" not in names_lower:
                    raise HTTPException(
                        status_code=400,
                        detail="Uploaded file is not a valid PDF or EPUB",
                    )
        except HTTPException:
            raise
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF or EPUB")
        file_extension = "epub"

    file_hash = hashlib.sha256(content).hexdigest()

    duplicate_status = await _content_service.check_duplicate_hash(
        session, current_user.id, file_hash
    )
    if duplicate_status in ("completed", "processing", "pending"):
        raise HTTPException(
            status_code=409,
            detail=f"Book already exists with status '{duplicate_status}'",
        )

    books_dir = os.path.join(settings.storage_root, "books")
    os.makedirs(books_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}.{file_extension}"
    rel_path = os.path.join("books", filename)
    abs_path = os.path.join(settings.storage_root, rel_path)

    with open(abs_path, "wb") as f:
        f.write(content)

    # Parse + chunk at upload time (fast). Workers only handle tokenization.
    has_smil = False
    try:
        if is_pdf:
            parsed = PdfParser(abs_path).parse()
        else:
            book_parser = BookParser(abs_path, "spine")
            parsed = book_parser.parse()
            has_smil = book_parser.detect_smil_overlays()
        chunks = BookChunker(parsed).chunk()
    except Exception as exc:
        os.remove(abs_path)
        fmt = "PDF" if is_pdf else "EPUB"
        raise HTTPException(status_code=400, detail=f"Could not parse {fmt}: {exc}")

    content_item = await _content_service.create_book_import(
        session,
        user_id=current_user.id,
        language_id=language_id,
        title=title,
        file_hash=file_hash,
        file_path=rel_path,
        description=description,
        register=register,
    )

    pages = [
        ContentPage(
            content_item_id=content_item.id,
            page_number=chunk.page_number,
            chapter_number=chunk.chapter_number,
            chapter_name=chunk.chapter_name,
            chapter_page_number=chunk.chapter_page_number,
            xhtml_file=chunk.xhtml_file,
            text=chunk.text,
        )
        for chunk in chunks
    ]
    session.add_all(pages)

    # Update chapter count on the Book row; set SMIL overlay flag if present
    book = await session.get(Book, content_item.id)
    if book:
        chapter_numbers = {c.chapter_number for c in chunks}
        book.chapter_count = max(chapter_numbers, default=0)
        if has_smil:
            book.has_audio_overlay = True
            book.audio_overlay_status = "pending"

    content_item.status = "processing"
    await session.commit()

    # Store total page count for worker progress tracking
    total_key = f"book:{content_item.id}:total_pages"
    await redis.setex(total_key, 86400, len(pages))

    # Enqueue one tokenize_page job per page (pages are now committed)
    for page in pages:
        await arq_pool.enqueue_job("tokenize_page", str(page.id))

    return BookUploadResponse(
        id=content_item.id,
        title=content_item.title,
        status=content_item.status,
        language_id=content_item.language_id,
    )


@router.get("", response_model=BookListResponse)
async def list_books(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BookListResponse:
    items = await _content_service.list_books(
        session, current_user.id, language_id=current_user.active_language_id
    )
    return BookListResponse(
        items=[BookListItem.model_validate(item) for item in items],
        total=len(items),
    )


@router.get("/{book_id}", response_model=BookDetailResponse)
async def get_book(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BookDetailResponse:
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    language = await session.get(Language, content_item.language_id)
    page_count = await session.scalar(
        sa.select(sa.func.count()).select_from(ContentPage).where(
            ContentPage.content_item_id == book_id
        )
    )

    has_audio = bool(book and book.audio_file_path)
    return BookDetailResponse(
        id=content_item.id,
        title=content_item.title,
        description=content_item.description,
        register=content_item.register,
        status=content_item.status,
        word_count=content_item.word_count,
        page_count=page_count,
        language_id=content_item.language_id,
        language_code=language.code if language else "unknown",
        chapter_count=book.chapter_count if book else None,
        created_at=content_item.created_at,
        has_audio=has_audio,
        audio_duration_ms=book.audio_duration_ms if book else None,
        has_audio_overlay=book.has_audio_overlay if book else False,
        audio_overlay_status=book.audio_overlay_status if book else "none",
        tts_status=book.tts_status if book else "none",
    )


@router.get("/{book_id}/pages", response_model=PageListResponse)
async def get_pages(
    book_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
    chapter: int | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PageListResponse:
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    pages, total = await _page_repo.get_pages_by_book(session, book_id, page, limit, chapter)

    # Collect unique lemmas from ready pages for words_map lookup.
    # lemma_map (surface → lemma) was built at import time (migration 0042).
    # Pre-migration pages have lemma_map=None; fall back to surface form as key.
    all_lemmas: set[str] = set()
    for p in pages:
        if p.status == "ready":
            lm = p.lemma_map or {}
            for sf in collect_surface_forms(p.text):
                all_lemmas.add(lm.get(sf, sf))

    words_map = await _word_repo.get_words_map(
        session,
        current_user.id,
        content_item.language_id,
        list(all_lemmas),
    )

    page_responses: list[PageResponse] = []
    for p in pages:
        enriched_tokens = (
            enrich_page_tokens(p.text, words_map, p.lemma_map) if p.status == "ready" else []
        )
        page_responses.append(
            PageResponse(
                id=p.id,
                page_number=p.page_number,
                chapter_number=p.chapter_number,
                chapter_name=p.chapter_name,
                chapter_page_number=p.chapter_page_number,
                status=p.status,
                text=p.text,
                tokens=enriched_tokens,
            )
        )

    return PageListResponse(items=page_responses, total=total, page=page, limit=limit)


@router.get("/{book_id}/chapters", response_model=list[ChapterSummary])
async def get_chapters(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ChapterSummary]:
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    result = await session.execute(
        sa.select(
            ContentPage.chapter_number,
            ContentPage.chapter_name,
            sa.func.min(ContentPage.page_number).label("first_page_number"),
            sa.func.count().label("page_count"),
        )
        .where(ContentPage.content_item_id == book_id)
        .group_by(ContentPage.chapter_number, ContentPage.chapter_name)
        .order_by(ContentPage.chapter_number)
    )
    return [
        ChapterSummary(
            chapter_number=row.chapter_number or 0,
            chapter_name=row.chapter_name,
            first_page_number=row.first_page_number,
            page_count=row.page_count,
        )
        for row in result
    ]


@router.get("/{book_id}/status/stream")
async def stream_import_status(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> EventSourceResponse:
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    current_status = content_item.status

    async def event_generator() -> AsyncGenerator[dict, None]:
        # If already in terminal state, emit one event and close
        if current_status in ("completed", "failed"):
            yield {"data": json.dumps({"event": current_status, "data": {}})}
            return

        channel = f"import:{book_id}"
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    payload = json.loads(message["data"])
                    yield {"data": json.dumps(payload)}
                    if payload.get("event") in ("completed", "failed"):
                        break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return EventSourceResponse(event_generator())


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    file_path = book.file_path if book else None
    audio_file_path = book.audio_file_path if book else None

    await _content_service.delete_book(session, book_id)
    await session.commit()

    settings = get_settings()
    for rel_path in filter(None, [file_path, audio_file_path]):
        abs_path = os.path.join(settings.storage_root, rel_path)
        try:
            os.remove(abs_path)
        except OSError:
            pass  # File already gone or never written — not fatal


# ---------------------------------------------------------------------------
# Audio routes (SMIL-only — no external upload)
# ---------------------------------------------------------------------------


@router.get("/{book_id}/audio/status", response_model=AudioStatusResponse)
async def get_audio_status(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AudioStatusResponse:
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    from src.infrastructure.db.models.audio import SentenceAlignment
    sentences_aligned = await session.scalar(
        sa.select(sa.func.count()).where(
            SentenceAlignment.page_id.in_(
                sa.select(ContentPage.id).where(ContentPage.content_item_id == book_id)
            )
        ).select_from(SentenceAlignment)
    ) or 0

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

    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != user_id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    overlay_status = book.audio_overlay_status if book else None

    async def event_generator() -> AsyncGenerator[dict, None]:
        if overlay_status in ("complete", "failed"):
            event = "complete" if overlay_status == "complete" else "failed"
            yield {"data": json.dumps({"event": event, "data": {}})}
            return

        channel = f"audio-align:{book_id}"
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
    token: str | None = Query(default=None, description="JWT token (for <audio> elements that cannot set headers)"),
    file_path: str | None = Query(default=None, description="Storage-relative path to a specific audio file"),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream audio file.

    Accepts Bearer Authorization header or ?token= query param.
    For SMIL books with multiple audio files, pass ?file_path= (from alignment response).
    Falls back to book.audio_file_path when file_path is not given.
    """
    import jwt as pyjwt
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

    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    settings = get_settings()

    if file_path:
        # Validate that the requested file is within this book's audio directory.
        # Use realpath to resolve symlinks before checking the prefix, which
        # prevents traversal via symlinks (normpath alone does not resolve them).
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


@router.delete("/{book_id}/audio", status_code=204)
async def delete_audio(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete extracted SMIL audio files and all sentence alignments for this book."""
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book or not book.has_audio_overlay:
        raise HTTPException(status_code=404, detail="No audio attached to this book")

    # Delete the entire audio directory for this book
    settings = get_settings()
    audio_dir = os.path.join(settings.storage_root, "books", str(book_id), "audio")
    if os.path.isdir(audio_dir):
        import shutil
        try:
            shutil.rmtree(audio_dir)
        except OSError:
            pass

    await _audio_repo.delete_alignments_for_book(session, book_id)

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
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    page = await session.scalar(
        sa.select(ContentPage).where(
            ContentPage.content_item_id == book_id,
            ContentPage.page_number == page_number,
        )
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    alignments = await _audio_repo.get_alignments_for_page(session, page.id)
    return [SentenceAlignmentResponse(**a) for a in alignments]


# ---------------------------------------------------------------------------
# TTS routes
# ---------------------------------------------------------------------------


@router.post("/{book_id}/audio/generate-tts", status_code=202)
async def generate_tts(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> dict:
    """Dispatch TTS generation for a book that has no embedded audio."""
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    if content_item.status != "completed":
        raise HTTPException(status_code=409, detail="Book is not yet fully tokenized")

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.tts_status in ("in_progress", "pending"):
        raise HTTPException(status_code=409, detail="TTS generation already in progress")

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
    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    pages_total = await session.scalar(
        sa.select(sa.func.count()).select_from(ContentPage).where(
            ContentPage.content_item_id == book_id
        )
    ) or 0

    pages_ready = await session.scalar(
        sa.select(sa.func.count()).select_from(ContentPage).where(
            ContentPage.content_item_id == book_id,
            ContentPage.tts_manifest_path.is_not(None),
        )
    ) or 0

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

    content_item = await _content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != user_id:
        raise HTTPException(status_code=404, detail="Book not found")

    settings = get_settings()

    # Validate path is within this book's TTS directory
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
