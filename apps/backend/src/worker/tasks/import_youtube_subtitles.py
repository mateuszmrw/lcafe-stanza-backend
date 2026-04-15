"""ARQ task for importing YouTube video subtitles and creating pages."""
import logging
import uuid

import sqlalchemy as sa
from redis.asyncio import Redis

from src.domain.youtube.chunker import YouTubeSubtitleChunker
from src.infrastructure.db.engine import AsyncSessionFactory
from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.youtube import YouTubeSubtitle
from src.infrastructure.db.repositories.audio_repo import AudioRepository
from src.worker.events import publish_import_event

logger = logging.getLogger(__name__)

_chunker = YouTubeSubtitleChunker()
_audio_repo = AudioRepository()
_REDIS_TTL = 86400  # 24 h


async def import_youtube_subtitles(
    ctx: dict,
    video_id: str,
    content_item_id: str,
    language_id: int,
) -> None:
    """Import YouTube video subtitles and create content pages.

    Args:
        ctx: ARQ context (contains redis)
        video_id: YouTube video ID
        content_item_id: Content item UUID string
        language_id: Language ID for the content item
    """
    content_item_uuid = uuid.UUID(content_item_id)
    redis: Redis = ctx["redis"]

    try:
        async with AsyncSessionFactory() as session:
            # Load subtitles for this video
            subtitle_rows = await session.execute(
                sa.select(YouTubeSubtitle)
                .where(YouTubeSubtitle.video_id == video_id)
                .order_by(YouTubeSubtitle.line_number)
            )
            subtitles = list(subtitle_rows.scalars().all())

            if not subtitles:
                logger.warning("No subtitles found for video %s", video_id)
                async with AsyncSessionFactory() as error_session:
                    content_item = await error_session.get(ContentItem, content_item_uuid)
                    if content_item:
                        content_item.status = "failed"
                        content_item.error_message = "No subtitles found"
                        await error_session.commit()
                return

            # Set initial status to processing
            content_item = await session.get(ContentItem, content_item_uuid)
            if content_item:
                content_item.status = "processing"
                await session.commit()

            # Convert subtitles to dicts for chunking
            subtitle_dicts = [
                {
                    "line_number": s.line_number,
                    "start_ms": s.start_ms,
                    "end_ms": s.end_ms,
                    "text": s.text,
                }
                for s in subtitles
            ]

            # Chunk subtitles into pages
            chunks = _chunker.chunk(subtitle_dicts, lines_per_page=20)

            # Create ContentPage rows for each chunk
            created_pages = []
            for page_number, chunk in enumerate(chunks, start=1):
                # Join subtitle texts with newlines
                page_text = "\n".join([line["text"] for line in chunk])

                page = ContentPage(
                    content_item_id=content_item_uuid,
                    page_number=page_number,
                    text=page_text,
                    status="pending",
                )
                session.add(page)
                created_pages.append(page)

            await session.flush()

            # Populate sentence_alignments immediately — subtitle line j → sentence_index j
            for page, chunk in zip(created_pages, chunks):
                alignments = [
                    {
                        "sentence_index": j,
                        "audio_start_ms": line["start_ms"],
                        "audio_end_ms": line["end_ms"],
                    }
                    for j, line in enumerate(chunk)
                ]
                await _audio_repo.upsert_alignments(session, page.id, alignments)

            await session.commit()

            logger.info(
                "Created %d pages for video %s (content_item=%s)",
                len(created_pages),
                video_id,
                content_item_uuid,
            )

        # Set Redis total_pages key
        total_pages = len(chunks)
        await redis.set(
            f"book:{content_item_uuid}:total_pages",
            str(total_pages),
            ex=_REDIS_TTL,
        )

        # Enqueue tokenize_page jobs for each page
        async with AsyncSessionFactory() as session:
            pages = await session.execute(
                sa.select(ContentPage)
                .where(ContentPage.content_item_id == content_item_uuid)
                .order_by(ContentPage.page_number)
            )
            pages_list = list(pages.scalars().all())

        for page in pages_list:
            await redis.enqueue_job("tokenize_page", str(page.id))  # type: ignore[attr-defined]

        # Publish progress event
        await publish_import_event(
            redis,
            content_item_uuid,
            "progress",
            {"step": "tokenizing", "pages_total": total_pages},
        )

        logger.info("YouTube import started: video=%s, pages=%d", video_id, total_pages)

    except Exception as exc:
        logger.exception("YouTube import failed for video %s: %s", video_id, exc)
        # Update content_item status to failed
        async with AsyncSessionFactory() as error_session:
            content_item = await error_session.get(ContentItem, content_item_uuid)
            if content_item:
                content_item.status = "failed"
                content_item.error_message = str(exc)
                await error_session.commit()

        # Publish failed event
        await publish_import_event(
            redis,
            content_item_uuid,
            "failed",
            {"error": str(exc)},
        )
