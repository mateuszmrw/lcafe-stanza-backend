from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.audio import SentenceAlignment


class AudioRepository:
    async def upsert_alignments(
        self,
        session: AsyncSession,
        page_id: uuid.UUID,
        alignments: list[dict],
    ) -> None:
        """Batch-insert sentence alignments. Ignores conflicts (idempotent)."""
        if not alignments:
            return
        rows = [
            {
                "id": uuid.uuid4(),
                "page_id": page_id,
                "sentence_index": a["sentence_index"],
                "audio_start_ms": a["audio_start_ms"],
                "audio_end_ms": a["audio_end_ms"],
                "audio_file": a.get("audio_file"),
            }
            for a in alignments
        ]
        stmt = sa.dialects.postgresql.insert(SentenceAlignment).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_sentence_alignment"
        )
        await session.execute(stmt)

    async def get_alignments_for_page(
        self, session: AsyncSession, page_id: uuid.UUID
    ) -> list[dict]:
        result = await session.execute(
            sa.select(
                SentenceAlignment.sentence_index,
                SentenceAlignment.audio_start_ms,
                SentenceAlignment.audio_end_ms,
                SentenceAlignment.audio_file,
            )
            .where(SentenceAlignment.page_id == page_id)
            .order_by(SentenceAlignment.sentence_index)
        )
        return [
            {
                "sentence_index": row.sentence_index,
                "audio_start_ms": row.audio_start_ms,
                "audio_end_ms": row.audio_end_ms,
                "audio_file": row.audio_file,
            }
            for row in result
        ]

    async def get_alignments_for_book(
        self, session: AsyncSession, book_id: uuid.UUID
    ) -> list[dict]:
        from src.infrastructure.db.models.content import ContentPage

        result = await session.execute(
            sa.select(
                SentenceAlignment.page_id,
                SentenceAlignment.sentence_index,
                SentenceAlignment.audio_start_ms,
                SentenceAlignment.audio_end_ms,
                SentenceAlignment.audio_file,
            )
            .join(ContentPage, ContentPage.id == SentenceAlignment.page_id)
            .where(ContentPage.content_item_id == book_id)
            .order_by(ContentPage.page_number, SentenceAlignment.sentence_index)
        )
        return [
            {
                "page_id": str(row.page_id),
                "sentence_index": row.sentence_index,
                "audio_start_ms": row.audio_start_ms,
                "audio_end_ms": row.audio_end_ms,
                "audio_file": row.audio_file,
            }
            for row in result
        ]

    async def get_alignment_for_sentence(
        self, session: AsyncSession, page_id: uuid.UUID, sentence_index: int
    ) -> dict | None:
        """Return a single alignment for a specific page + sentence, or None."""
        result = await session.execute(
            sa.select(
                SentenceAlignment.audio_start_ms,
                SentenceAlignment.audio_end_ms,
                SentenceAlignment.audio_file,
            )
            .where(
                SentenceAlignment.page_id == page_id,
                SentenceAlignment.sentence_index == sentence_index,
            )
            .limit(1)
        )
        row = result.one_or_none()
        if not row:
            return None
        return {
            "audio_start_ms": row.audio_start_ms,
            "audio_end_ms": row.audio_end_ms,
            "audio_file": row.audio_file,
        }

    async def get_time_index(
        self, session: AsyncSession, book_id: uuid.UUID
    ) -> list[dict]:
        from src.infrastructure.db.models.content import ContentPage

        result = await session.execute(
            sa.select(
                ContentPage.page_number,
                SentenceAlignment.sentence_index,
                SentenceAlignment.audio_start_ms,
                SentenceAlignment.audio_end_ms,
            )
            .join(ContentPage, ContentPage.id == SentenceAlignment.page_id)
            .where(ContentPage.content_item_id == book_id)
            .order_by(ContentPage.page_number, SentenceAlignment.sentence_index)
        )
        return [
            {
                "page_number": row.page_number,
                "sentence_index": row.sentence_index,
                "start_ms": row.audio_start_ms,
                "end_ms": row.audio_end_ms,
            }
            for row in result
        ]

    async def delete_alignments_for_book(
        self, session: AsyncSession, book_id: uuid.UUID
    ) -> None:
        from src.infrastructure.db.models.content import ContentPage

        page_ids_subq = sa.select(ContentPage.id).where(
            ContentPage.content_item_id == book_id
        )
        await session.execute(
            sa.delete(SentenceAlignment).where(
                SentenceAlignment.page_id.in_(page_ids_subq)
            )
        )
