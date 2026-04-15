"""generate_tts_audio — ARQ task to generate per-page TTS audio for a book.

For each page:
  1. Split text into sentences
  2. Generate/fetch cached per-sentence MP3 via TtsService
  3. Concatenate and DASH-segment into a per-page manifest
  4. Persist sentence_alignments with cumulative timestamps
  5. Store manifest path on content_pages

Publishes Redis progress events on channel `tts-gen:{book_id}`.
"""

from __future__ import annotations

import json
import logging
import uuid

import sqlalchemy as sa
from redis.asyncio import Redis

from src.domain.tts.service import TtsService
from src.infrastructure.db.engine import AsyncSessionFactory
from src.infrastructure.db.models.content import Book, ContentItem, ContentPage
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.repositories.audio_repo import AudioRepository

logger = logging.getLogger(__name__)

_tts_service = TtsService()
_audio_repo = AudioRepository()


async def generate_tts_audio(ctx: dict, book_id: str) -> None:
    book_uuid = uuid.UUID(book_id)
    redis: Redis = ctx["redis"]

    async with AsyncSessionFactory() as session:
        book = await session.get(Book, book_uuid)
        if book is None:
            logger.error("Book %s not found", book_uuid)
            return

        content_item = await session.get(ContentItem, book_uuid)
        if content_item is None:
            logger.error("ContentItem %s not found", book_uuid)
            return

        lang = await session.get(Language, content_item.language_id)
        language_code = lang.code if lang else ""

        if not _tts_service.supports_language(language_code):
            logger.info("Language %s not supported by TTS, skipping book %s", language_code, book_uuid)
            book.tts_status = "failed"
            await session.commit()
            return

        book.tts_status = "in_progress"
        await session.commit()

    logger.info("TTS generation starting for book %s (%s)", book_uuid, language_code)

    try:
        async with AsyncSessionFactory() as session:
            rows = await session.execute(
                sa.select(ContentPage.id, ContentPage.page_number, ContentPage.text)
                .where(
                    ContentPage.content_item_id == book_uuid,
                    ContentPage.status == "ready",
                )
                .order_by(ContentPage.page_number)
            )
            pages = list(rows)

        total = len(pages)
        completed = 0

        for page_id, page_number, text in pages:
            sentences = [s.strip() for s in text.replace("\n\n", "\n").split("\n") if s.strip()]
            if not sentences:
                completed += 1
                continue

            async with AsyncSessionFactory() as session:
                result = await _tts_service.build_page_dash(
                    session,
                    book_uuid,
                    page_number,
                    sentences,
                    language_code,
                )
                await session.commit()

            if result is None:
                logger.warning("Page %s/%d: TTS returned no result", book_id, page_number)
                completed += 1
                continue

            manifest_rel, alignments = result

            async with AsyncSessionFactory() as session:
                await session.execute(
                    sa.update(ContentPage)
                    .where(ContentPage.id == page_id)
                    .values(tts_manifest_path=manifest_rel)
                )

                alignment_rows = [
                    {
                        "sentence_index": i,
                        "audio_start_ms": start,
                        "audio_end_ms": end,
                        "audio_file": manifest_rel,
                    }
                    for i, (start, end) in enumerate(alignments)
                ]
                await _audio_repo.upsert_alignments(session, page_id, alignment_rows)
                await session.commit()

            completed += 1
            await redis.publish(
                f"tts-gen:{book_uuid}",
                json.dumps({
                    "event": "progress",
                    "data": {"completed": completed, "total": total},
                }),
            )

        async with AsyncSessionFactory() as session:
            book = await session.get(Book, book_uuid)
            if book:
                book.tts_status = "complete"
            await session.commit()

        logger.info("TTS generation complete for book %s: %d pages", book_uuid, total)
        await redis.publish(
            f"tts-gen:{book_uuid}",
            json.dumps({"event": "complete", "data": {"pages": total}}),
        )

    except Exception as exc:
        logger.exception("TTS generation failed for book %s: %s", book_uuid, exc)
        async with AsyncSessionFactory() as session:
            book = await session.get(Book, book_uuid)
            if book:
                book.tts_status = "failed"
            await session.commit()

        await redis.publish(
            f"tts-gen:{book_uuid}",
            json.dumps({"event": "failed", "data": {"error": str(exc)}}),
        )
