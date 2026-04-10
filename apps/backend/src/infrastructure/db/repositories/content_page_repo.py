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
