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

    async def get_books_meta_by_ids(
        self, session: AsyncSession, content_item_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[str | None, bool, str | None]]:
        """Return {id: (cover_image_path, has_audio_overlay, audio_overlay_status)} for the given books."""
        if not content_item_ids:
            return {}
        rows = await session.execute(
            sa.select(
                Book.content_item_id,
                Book.cover_image_path,
                Book.has_audio_overlay,
                Book.audio_overlay_status,
            ).where(Book.content_item_id.in_(content_item_ids))
        )
        return {
            row.content_item_id: (
                row.cover_image_path,
                row.has_audio_overlay,
                row.audio_overlay_status,
            )
            for row in rows
        }

    async def count_books_for_user_language(
        self, session: AsyncSession, user_id: uuid.UUID, language_id: int
    ) -> int:
        result = await session.scalar(
            sa.select(sa.func.count())
            .select_from(ContentItem)
            .where(
                ContentItem.user_id == user_id,
                ContentItem.language_id == language_id,
                ContentItem.type == "book",
            )
        )
        return result or 0

    async def list_book_file_paths_for_user(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> list[str]:
        """Return every storage-relative file_path/audio_file_path owned by this user."""
        result = await session.execute(
            sa.select(Book.file_path, Book.audio_file_path)
            .join(ContentItem, Book.content_item_id == ContentItem.id)
            .where(ContentItem.user_id == user_id)
        )
        return [p for row in result for p in row if p]

    async def delete_all_for_user(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> int:
        result = await session.execute(
            sa.delete(ContentItem).where(ContentItem.user_id == user_id)
        )
        return result.rowcount  # type: ignore[return-value]

    async def delete_all(self, session: AsyncSession) -> int:
        result = await session.execute(sa.delete(ContentItem))
        return result.rowcount  # type: ignore[return-value]
