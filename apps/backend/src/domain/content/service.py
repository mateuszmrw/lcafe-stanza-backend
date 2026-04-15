from __future__ import annotations

import uuid
from typing import Literal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.content import Book, ContentItem


class ContentService:
    async def check_duplicate_hash(
        self, session: AsyncSession, user_id: uuid.UUID, file_hash: str
    ) -> Literal["completed", "processing", "failed", "pending"] | None:
        """Return the status of an existing book with the same hash, or None if no duplicate."""
        result = await session.execute(
            sa.select(ContentItem.status)
            .join(Book, Book.content_item_id == ContentItem.id)
            .where(ContentItem.user_id == user_id, Book.file_hash == file_hash)
        )
        row = result.scalar_one_or_none()
        return row  # type: ignore[return-value]

    async def create_book_import(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        title: str,
        file_hash: str,
        file_path: str,
        description: str | None = None,
        register: str | None = None,
    ) -> ContentItem:
        content_item = ContentItem(
            user_id=user_id,
            language_id=language_id,
            type="book",
            title=title,
            description=description,
            register=register,
            status="pending",
        )
        session.add(content_item)
        await session.flush()  # populate content_item.id

        book = Book(
            content_item_id=content_item.id,
            file_hash=file_hash,
            file_path=file_path,
        )
        session.add(book)
        await session.flush()
        return content_item

    async def get_book(
        self, session: AsyncSession, content_item_id: uuid.UUID
    ) -> ContentItem | None:
        result = await session.execute(
            sa.select(ContentItem).where(ContentItem.id == content_item_id)
        )
        return result.scalar_one_or_none()

    async def list_books(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int | None = None,
    ) -> list[ContentItem]:
        query = (
            sa.select(ContentItem)
            .where(ContentItem.user_id == user_id, ContentItem.type == "book")
            .order_by(ContentItem.created_at.desc())
        )
        if language_id is not None:
            query = query.where(ContentItem.language_id == language_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def delete_book(
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
