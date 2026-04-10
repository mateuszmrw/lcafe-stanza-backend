import hashlib
import io
import json
import os
import re
import uuid
import zipfile
from typing import AsyncGenerator

from arq import ArqRedis
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from redis.asyncio import Redis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import get_arq_pool, get_current_user, get_db, get_redis
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
from src.domain.content.service import ContentService
from src.domain.nlp.services.book_chunker import BookChunker
from src.domain.nlp.services.book_parser import BookParser
from src.infrastructure.db.models.content import Book, ContentPage
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.content_page_repo import ContentPageRepository
from src.infrastructure.db.repositories.word_repo import WordRepository

# Matches individual word tokens (letters/digits only) — used for vocabulary lookups.
_WORD_RE = re.compile(r"\b\w+\b")
# Matches words OR individual punctuation/symbol characters (not whitespace).
# Used when building the full token list for the reader, so punctuation is preserved.
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")

router = APIRouter(prefix="/books", tags=["books"])
_content_service = ContentService()
_page_repo = ContentPageRepository()
_word_repo = WordRepository()


@router.post("", response_model=BookUploadResponse, status_code=201)
async def upload_book(
    language_id: int = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
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

    content = await file.read()

    # Validate EPUB structure before touching disk (case-insensitive — some EPUBs
    # produced on macOS use lower-case "meta-inf/container.xml").
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names_lower = {n.lower() for n in zf.namelist()}
            if "meta-inf/container.xml" not in names_lower:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is missing META-INF/container.xml — not a valid EPUB",
                )
    except HTTPException:
        raise
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP/EPUB archive")

    file_hash = hashlib.sha256(content).hexdigest()

    duplicate_status = await _content_service.check_duplicate_hash(
        session, current_user.id, file_hash
    )
    if duplicate_status in ("completed", "processing", "pending"):
        raise HTTPException(
            status_code=409,
            detail=f"Book already exists with status '{duplicate_status}'",
        )

    settings = get_settings()
    books_dir = os.path.join(settings.storage_root, "books")
    os.makedirs(books_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}.epub"
    rel_path = os.path.join("books", filename)
    abs_path = os.path.join(settings.storage_root, rel_path)

    with open(abs_path, "wb") as f:
        f.write(content)

    # Parse + chunk the EPUB at upload time (fast, ~1s).
    # Workers only receive tokenization jobs — no parsing overhead per worker.
    try:
        chunks = BookChunker(BookParser(abs_path, "spine").parse()).chunk()
    except Exception as exc:
        os.remove(abs_path)
        raise HTTPException(status_code=400, detail=f"Could not parse EPUB: {exc}")

    content_item = await _content_service.create_book_import(
        session,
        user_id=current_user.id,
        language_id=language_id,
        title=title,
        file_hash=file_hash,
        file_path=rel_path,
        description=description,
    )

    pages = [
        ContentPage(
            content_item_id=content_item.id,
            page_number=chunk.page_number,
            chapter_number=chunk.chapter_number,
            chapter_name=chunk.chapter_name,
            chapter_page_number=chunk.chapter_page_number,
            text=chunk.text,
        )
        for chunk in chunks
    ]
    session.add_all(pages)

    # Update chapter count on the Book row
    book = await session.get(Book, content_item.id)
    if book:
        chapter_numbers = {c.chapter_number for c in chunks}
        book.chapter_count = max(chapter_numbers, default=0)

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

    return BookDetailResponse(
        id=content_item.id,
        title=content_item.title,
        description=content_item.description,
        status=content_item.status,
        word_count=content_item.word_count,
        page_count=page_count,
        language_id=content_item.language_id,
        language_code=language.code if language else "unknown",
        chapter_count=book.chapter_count if book else None,
        created_at=content_item.created_at,
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

    # Collect unique surface forms only from ready pages (pending pages have no words yet).
    all_surface_forms: list[str] = []
    for p in pages:
        if p.status == "ready":
            for m in _WORD_RE.finditer(p.text):
                all_surface_forms.append(m.group(0).lower())

    words_map = await _word_repo.get_words_map(
        session,
        current_user.id,
        content_item.language_id,
        list(set(all_surface_forms)),
    )

    page_responses: list[PageResponse] = []
    for p in pages:
        enriched_tokens: list[TokenWithStatus] = []
        if p.status == "ready":
            # Split on double newlines for paragraphs, single newlines for sentences.
            # Both formats exist: new imports use \n\n, legacy data uses \r?\n.
            paragraphs = re.split(r"\n\n+", p.text)
            global_si = 0
            for pi, paragraph in enumerate(paragraphs):
                sentences = [s for s in re.split(r"\r?\n", paragraph) if s.strip()]
                if not sentences:
                    sentences = [paragraph]
                for sentence in sentences:
                    for m in _TOKEN_RE.finditer(sentence):
                        surface = m.group(0)
                        is_punct = not (surface[0].isalnum() or surface[0] == "_")
                        if is_punct:
                            enriched_tokens.append(
                                TokenWithStatus(
                                    w=surface,
                                    l="",
                                    pos="PUNCT",
                                    r="",
                                    pi=pi,
                                    si=global_si,
                                    g="",
                                    f="",
                                    dep_head=0,
                                    dep_rel="",
                                    status="ignored",
                                )
                            )
                        else:
                            key = surface.lower()
                            word_data = words_map.get(key, {})
                            enriched_tokens.append(
                                TokenWithStatus(
                                    id=word_data.get("id"),
                                    w=surface,
                                    l=word_data.get("lemma", ""),
                                    pos=word_data.get("pos", ""),
                                    r=word_data.get("reading", ""),
                                    pi=pi,
                                    si=global_si,
                                    g=word_data.get("gender", ""),
                                    f=word_data.get("feats", ""),
                                    dep_head=word_data.get("dep_head", 0),
                                    dep_rel=word_data.get("dep_rel", ""),
                                    status=word_data.get("status", "new"),
                                )
                            )
                    global_si += 1
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

    await _content_service.delete_book(session, book_id)
    await session.commit()

    if file_path:
        settings = get_settings()
        abs_path = os.path.join(settings.storage_root, file_path)
        try:
            os.remove(abs_path)
        except OSError:
            pass  # File already gone or never written — not fatal
