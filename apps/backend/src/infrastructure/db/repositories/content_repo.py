from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.content import Book, ContentItem


class ContentRepository:
    async def create_content_item(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        type: str,
        title: str,
        description: str | None = None,
    ) -> ContentItem:
        item = ContentItem(
            user_id=user_id,
            language_id=language_id,
            type=type,
            title=title,
            description=description,
        )
        session.add(item)
        await session.flush()
        return item

    async def create_book(
        self,
        session: AsyncSession,
        content_item_id: uuid.UUID,
        file_hash: str,
        file_path: str,
    ) -> Book:
        book = Book(
            content_item_id=content_item_id,
            file_hash=file_hash,
            file_path=file_path,
        )
        session.add(book)
        await session.flush()
        return book

    async def find_by_id(
        self, session: AsyncSession, content_item_id: uuid.UUID
    ) -> ContentItem | None:
        result = await session.execute(
            sa.select(ContentItem).where(ContentItem.id == content_item_id)
        )
        return result.scalar_one_or_none()

    async def find_by_hash(
        self, session: AsyncSession, user_id: uuid.UUID, file_hash: str
    ) -> ContentItem | None:
        result = await session.execute(
            sa.select(ContentItem)
            .join(Book, Book.content_item_id == ContentItem.id)
            .where(ContentItem.user_id == user_id, Book.file_hash == file_hash)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> list[ContentItem]:
        result = await session.execute(
            sa.select(ContentItem)
            .where(ContentItem.user_id == user_id)
            .order_by(ContentItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(
        self, session: AsyncSession, content_item_id: uuid.UUID
    ) -> None:
        await session.execute(
            sa.delete(ContentItem).where(ContentItem.id == content_item_id)
        )

    async def update_status(
        self,
        session: AsyncSession,
        content_item_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
    ) -> None:
        values: dict = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        await session.execute(
            sa.update(ContentItem)
            .where(ContentItem.id == content_item_id)
            .values(**values)
        )
