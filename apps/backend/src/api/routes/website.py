"""Website article import API routes."""
from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_arq_pool, get_current_user, get_db, get_redis
from src.api.schemas.website import (
    WebsiteImportRequest,
    WebsiteImportResponse,
    WebsitePreviewRequest,
    WebsitePreviewResponse,
)
from src.domain.content.service import ContentService
from src.domain.nlp.services.text_parser import TextParser
from src.infrastructure.db.models.content import ContentPage
from src.infrastructure.db.models.users import User
from src.infrastructure.web.extractor import ExtractionError, WebArticleExtractor

router = APIRouter(prefix="/website", tags=["website"])
_extractor = WebArticleExtractor()
_content_service = ContentService()


@router.post("/preview", response_model=WebsitePreviewResponse)
async def preview_website(
    request: WebsitePreviewRequest,
) -> WebsitePreviewResponse:
    """Extract article metadata for preview. No database writes."""
    try:
        result = await _extractor.extract(request.url)
    except ExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    word_count = len(result.text.split())

    return WebsitePreviewResponse(
        url=request.url,
        title=result.title,
        excerpt=result.excerpt,
        word_count=word_count,
        author=result.author,
    )


@router.post("/import", response_model=WebsiteImportResponse, status_code=202)
async def import_website(
    request: WebsiteImportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
    redis: Redis = Depends(get_redis),
) -> WebsiteImportResponse:
    """Import a website article. Creates ContentItem + pages, enqueues tokenization."""
    if current_user.active_language_id is None:
        raise HTTPException(status_code=400, detail="Set an active language before importing")
    if request.language_id != current_user.active_language_id:
        raise HTTPException(status_code=400, detail="Import language must match your active language")

    try:
        result = await _extractor.extract(request.url)
    except ExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    content_item = await _content_service.create_website_import(
        session,
        user_id=current_user.id,
        language_id=request.language_id,
        title=request.title or result.title,
        source_url=request.url,
    )

    # Chunk text into pages
    chunks = TextParser(result.text, chunkSize=3000).parse()

    pages = [
        ContentPage(
            content_item_id=content_item.id,
            page_number=i,
            text=chunk,
        )
        for i, chunk in enumerate(chunks, start=1)
    ]
    session.add_all(pages)

    content_item.status = "processing"
    await session.commit()

    # Store total page count for worker progress tracking
    await redis.setex(f"book:{content_item.id}:total_pages", 86400, len(pages))

    # Enqueue tokenize_page jobs
    for page in pages:
        await arq_pool.enqueue_job("tokenize_page", str(page.id))

    return WebsiteImportResponse(
        id=str(content_item.id),
        title=content_item.title,
        status=content_item.status,
        language_id=content_item.language_id,
    )
