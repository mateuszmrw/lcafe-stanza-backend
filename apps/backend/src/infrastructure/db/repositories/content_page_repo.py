from __future__ import annotations

import uuid
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.content import ContentPage


@dataclass
class PageData:
    page_number: int
    text: str
    tokens: list | None = None
    chapter_number: int | None = None
    chapter_name: str | None = None
    chapter_page_number: int | None = None


class ContentPageRepository:
    async def bulk_insert_pages(
        self,
        session: AsyncSession,
        content_item_id: uuid.UUID,
        pages: list[PageData],
    ) -> None:
        if not pages:
            return
        rows = [
            {
                "content_item_id": content_item_id,
                "page_number": p.page_number,
                "text": p.text,
                "tokens": p.tokens,
                "chapter_number": p.chapter_number,
                "chapter_name": p.chapter_name,
                "chapter_page_number": p.chapter_page_number,
            }
            for p in pages
        ]
        stmt = (
            pg_insert(ContentPage)
            .values(rows)
            .on_conflict_do_nothing(
                index_elements=["content_item_id", "page_number"]
            )
        )
        await session.execute(stmt)

    async def count_by_book(
        self, session: AsyncSession, content_item_id: uuid.UUID
    ) -> int:
        result = await session.scalar(
            sa.select(sa.func.count())
            .select_from(ContentPage)
            .where(ContentPage.content_item_id == content_item_id)
        )
        return result or 0

    async def count_tts_ready(
        self, session: AsyncSession, content_item_id: uuid.UUID
    ) -> int:
        result = await session.scalar(
            sa.select(sa.func.count())
            .select_from(ContentPage)
            .where(
                ContentPage.content_item_id == content_item_id,
                ContentPage.tts_manifest_path.is_not(None),
            )
        )
        return result or 0

    async def get_by_book_and_page_number(
        self,
        session: AsyncSession,
        content_item_id: uuid.UUID,
        page_number: int,
    ) -> ContentPage | None:
        return await session.scalar(
            sa.select(ContentPage).where(
                ContentPage.content_item_id == content_item_id,
                ContentPage.page_number == page_number,
            )
        )

    async def list_by_book(
        self, session: AsyncSession, content_item_id: uuid.UUID
    ) -> list[ContentPage]:
        result = await session.execute(
            sa.select(ContentPage)
            .where(ContentPage.content_item_id == content_item_id)
            .order_by(ContentPage.page_number)
        )
        return list(result.scalars().all())

    async def list_chapters(
        self, session: AsyncSession, content_item_id: uuid.UUID
    ) -> list[dict]:
        """Return [{chapter_number, chapter_name, first_page_number, page_count}] per chapter."""
        result = await session.execute(
            sa.select(
                ContentPage.chapter_number,
                ContentPage.chapter_name,
                sa.func.min(ContentPage.page_number).label("first_page_number"),
                sa.func.count().label("page_count"),
            )
            .where(ContentPage.content_item_id == content_item_id)
            .group_by(ContentPage.chapter_number, ContentPage.chapter_name)
            .order_by(ContentPage.chapter_number)
        )
        return [
            {
                "chapter_number": row.chapter_number or 0,
                "chapter_name": row.chapter_name,
                "first_page_number": row.first_page_number,
                "page_count": row.page_count,
            }
            for row in result
        ]

    async def count_ready_for_user_language(
        self, session: AsyncSession, user_id: uuid.UUID, language_id: int
    ) -> int:
        """Count 'ready' pages across all books for a given user+language."""
        from src.infrastructure.db.models.content import ContentItem

        result = await session.scalar(
            sa.select(sa.func.count())
            .select_from(ContentPage)
            .join(ContentItem, ContentItem.id == ContentPage.content_item_id)
            .where(
                ContentItem.user_id == user_id,
                ContentItem.language_id == language_id,
                ContentPage.status == "ready",
            )
        )
        return result or 0

    async def find_sentence_for_lemma(
        self,
        session: AsyncSession,
        lemma: str,
        content_item_id: uuid.UUID,
    ) -> dict | None:
        """Return one sentence containing a token with the given lemma.

        Prefers the most recent page. Returns
        {"tokens": [...], "page_number": int, "target_index": int} or None.
        """
        result = await session.execute(
            sa.text(
                """
                SELECT p.page_number,
                       p.tokens,
                       (elem.value->>'si')::int AS sentence_idx,
                       (elem.ordinality - 1)::int AS token_idx
                FROM content_pages p
                CROSS JOIN LATERAL
                    jsonb_array_elements(p.tokens) WITH ORDINALITY AS elem(value, ordinality)
                WHERE p.content_item_id = :content_item_id
                  AND p.tokens IS NOT NULL
                  AND elem.value->>'l' = :lemma
                ORDER BY p.page_number DESC
                LIMIT 1
                """
            ),
            {"content_item_id": content_item_id, "lemma": lemma},
        )
        row = result.first()
        if row is None:
            return None

        all_tokens: list[dict] = row.tokens
        sentence_idx: int = row.sentence_idx
        sentence_tokens = [t for t in all_tokens if t.get("si") == sentence_idx]
        target_index = next(
            (i for i, t in enumerate(sentence_tokens) if t.get("l") == lemma),
            0,
        )
        return {
            "tokens": sentence_tokens,
            "page_number": row.page_number,
            "target_index": target_index,
        }

    async def get_pages_by_book(
        self,
        session: AsyncSession,
        content_item_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        chapter: int | None = None,
    ) -> tuple[list[ContentPage], int]:
        base = sa.select(ContentPage).where(
            ContentPage.content_item_id == content_item_id
        )
        if chapter is not None:
            base = base.where(ContentPage.chapter_number == chapter)

        total_result = await session.execute(
            sa.select(sa.func.count()).select_from(base.subquery())
        )
        total = total_result.scalar_one()

        result = await session.execute(
            base.order_by(ContentPage.page_number)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return list(result.scalars().all()), total
