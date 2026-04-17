import hashlib
import io
import json
import logging
import os
import uuid
import zipfile
from typing import AsyncGenerator

from arq import ArqRedis
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import get_arq_pool, get_current_user, get_db, get_redis
from src.domain.content.import_service import (
    IMPORT_CHANNEL,
    set_total_pages,
)
from src.api.schemas.books import (
    BookDetailResponse,
    BookListItem,
    BookListResponse,
    BookUploadResponse,
)
from src.core.config import get_settings
from src.domain.nlp.services.book_chunker import BookChunker
from src.domain.nlp.services.book_parser import BookParser
from src.domain.nlp.services.pdf_parser import PdfParser
from src.infrastructure.db.models.content import Book, ContentPage
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.users import User

from ._deps import content_repo, content_service, coverage_service, page_repo

router = APIRouter(prefix="/books", tags=["books"])


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
        raise HTTPException(
            status_code=400, detail="Set an active language before importing books"
        )
    if language_id != current_user.active_language_id:
        raise HTTPException(
            status_code=400, detail="Book language must match your active language"
        )

    settings = get_settings()
    content = await file.read(settings.max_book_upload_bytes + 1)
    if len(content) > settings.max_book_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {settings.max_book_upload_bytes // (1024 * 1024)} MB.",
        )

    _PDF_MAGIC = b"%PDF"
    is_pdf = content[:4] == _PDF_MAGIC

    if is_pdf:
        file_extension = "pdf"
    else:
        # Case-insensitive container.xml lookup — some macOS-produced EPUBs use lowercase paths.
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
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid PDF or EPUB"
            )
        file_extension = "epub"

    file_hash = hashlib.sha256(content).hexdigest()

    duplicate_status = await content_service.check_duplicate_hash(
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

    has_smil = False
    cover: tuple[str, bytes] | None = None
    try:
        if is_pdf:
            parsed = PdfParser(abs_path).parse()
        else:
            book_parser = BookParser(abs_path, "spine")
            parsed = book_parser.parse()
            has_smil = book_parser.detect_smil_overlays()
            cover = book_parser.extract_cover_image()
        chunks = BookChunker(parsed).chunk()
    except Exception as exc:
        os.remove(abs_path)
        fmt = "PDF" if is_pdf else "EPUB"
        raise HTTPException(status_code=400, detail=f"Could not parse {fmt}: {exc}")

    content_item = await content_service.create_book_import(
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

    book = await session.get(Book, content_item.id)
    if book:
        chapter_numbers = {c.chapter_number for c in chunks}
        book.chapter_count = max(chapter_numbers, default=0)
        if has_smil:
            book.has_audio_overlay = True
            book.audio_overlay_status = "pending"
        if cover is not None:
            media_type, cover_bytes = cover
            ext = BookParser.cover_extension_for(media_type)
            cover_dir = os.path.join(
                settings.storage_root, "books", str(content_item.id)
            )
            os.makedirs(cover_dir, exist_ok=True)
            cover_rel = os.path.join("books", str(content_item.id), f"cover.{ext}")
            cover_abs = os.path.join(settings.storage_root, cover_rel)
            try:
                with open(cover_abs, "wb") as f:
                    f.write(cover_bytes)
                book.cover_image_path = cover_rel
            except OSError:
                logging.getLogger().exception(
                    "Failed to write cover image for book %s", content_item.id
                )

    content_item.status = "processing"
    await session.commit()

    await set_total_pages(redis, content_item.id, len(pages))

    # If enqueue fails partway through, mark the book failed so the user doesn't
    # see it stuck in "processing" forever.
    try:
        for page in pages:
            await arq_pool.enqueue_job("tokenize_page", str(page.id))
    except Exception:
        content_item.status = "failed"
        content_item.error_message = "Failed to enqueue tokenization jobs"
        await session.commit()
        raise

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
    redis: Redis = Depends(get_redis),
) -> BookListResponse:
    items = await content_service.list_books(
        session, current_user.id, language_id=current_user.active_language_id
    )

    # Skip coverage when user has no active language — language_id=0 would query
    # a non-existent language and silently return null for every book.
    coverage_map: dict = {}
    if current_user.active_language_id is not None:
        completed_ids = [item.id for item in items if item.status == "completed"]
        coverage_map = await coverage_service.compute_book_coverages(
            session, redis, current_user.id,
            current_user.active_language_id,
            completed_ids,
        )

    book_ids = [item.id for item in items]
    book_meta_map = await content_repo.get_books_meta_by_ids(session, book_ids)

    book_items = []
    for item in items:
        bi = BookListItem.model_validate(item)
        pair = coverage_map.get(item.id)
        if pair is not None:
            bi.coverage_pct, bi.mastered_pct = pair
        meta = book_meta_map.get(item.id)
        if meta is not None:
            cover_path, has_overlay, overlay_status = meta
            bi.has_cover = bool(cover_path)
            bi.has_audio_overlay = bool(has_overlay)
            bi.audio_overlay_status = overlay_status or "none"
        book_items.append(bi)

    return BookListResponse(items=book_items, total=len(items))


@router.get("/{book_id}", response_model=BookDetailResponse)
async def get_book(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BookDetailResponse:
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    language = await session.get(Language, content_item.language_id)
    page_count = await page_repo.count_by_book(session, book_id)

    video_id: str | None = None
    if content_item.type == "youtube":
        from src.infrastructure.db.models.youtube import YouTubeVideo

        yt = await session.get(YouTubeVideo, book_id)
        video_id = yt.video_id if yt else None

    has_audio = bool(book and book.audio_file_path)
    return BookDetailResponse(
        id=content_item.id,
        type=content_item.type,
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
        video_id=video_id,
        source_url=content_item.source_url,
        has_cover=bool(book and book.cover_image_path),
    )


@router.get("/{book_id}/status/stream")
async def stream_import_status(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> EventSourceResponse:
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    current_status = content_item.status

    async def event_generator() -> AsyncGenerator[dict, None]:
        if current_status in ("completed", "failed"):
            yield {"data": json.dumps({"event": current_status, "data": {}})}
            return

        channel = IMPORT_CHANNEL.format(book_id=book_id)
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
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    book = await session.get(Book, book_id)
    file_path = book.file_path if book else None
    audio_file_path = book.audio_file_path if book else None
    cover_image_path = book.cover_image_path if book else None

    await content_service.delete_book(session, book_id)
    await session.commit()

    settings = get_settings()
    for rel_path in filter(None, [file_path, audio_file_path, cover_image_path]):
        abs_path = os.path.join(settings.storage_root, rel_path)
        try:
            os.remove(abs_path)
        except OSError:
            pass


__all__ = ["router"]
