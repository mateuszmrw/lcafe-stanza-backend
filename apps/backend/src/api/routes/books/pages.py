import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas.books import (
    ChapterSummary,
    PageListResponse,
    PageResponse,
)
from src.domain.content.page_enricher import collect_surface_forms, enrich_page_tokens
from src.domain.nlp.constituency import phrases_for_page
from src.infrastructure.db.models.content import ContentPage
from src.infrastructure.db.models.users import User

from ._deps import content_service, page_repo, word_repo

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/{book_id}/pages", response_model=PageListResponse)
async def get_pages(
    book_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
    chapter: int | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PageListResponse:
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    pages, total = await page_repo.get_pages_by_book(
        session, book_id, page, limit, chapter
    )

    # lemma_map (surface → lemma) built at import time since migration 0042.
    # Pre-migration pages have lemma_map=None; fall back to surface form as key.
    all_lemmas: set[str] = set()
    for p in pages:
        if p.status == "ready":
            lm = p.lemma_map or {}
            for sf in collect_surface_forms(p.text):
                all_lemmas.add(lm.get(sf, sf))

    words_map = await word_repo.get_words_map(
        session,
        current_user.id,
        content_item.language_id,
        list(all_lemmas),
    )

    page_responses: list[PageResponse] = []
    for p in pages:
        enriched_tokens = (
            enrich_page_tokens(p.text, words_map, p.lemma_map, p.tokens)
            if p.status == "ready"
            else []
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


@router.get("/{book_id}/pages/{page_id}/phrases")
async def get_page_phrases(
    book_id: uuid.UUID,
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return phrase boundary spans extracted from constituency parse trees.

    Each phrase is {"si": sentence_idx, "start": word_start, "end": word_end,
    "type": phrase_type, "text": surface_text}.

    Returns [] when constituency data is not yet available (page not tokenized
    with a 1.11+ pipeline, or language has no constituency model).
    """
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    page = await session.get(ContentPage, page_id)
    if not page or page.content_item_id != book_id:
        raise HTTPException(status_code=404, detail="Page not found")

    if not page.constituency or not page.tokens:
        return []

    return phrases_for_page(page.constituency, page.tokens)


@router.get("/{book_id}/chapters", response_model=list[ChapterSummary])
async def get_chapters(
    book_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ChapterSummary]:
    content_item = await content_service.get_book(session, book_id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found")

    rows = await page_repo.list_chapters(session, book_id)
    return [ChapterSummary(**row) for row in rows]


__all__ = ["router"]
