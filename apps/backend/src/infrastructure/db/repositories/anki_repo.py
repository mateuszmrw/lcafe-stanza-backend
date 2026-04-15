from __future__ import annotations

import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.anki import AnkiSettings
from src.infrastructure.db.models.words import Word


class AnkiRepository:
    async def get_settings(self, session: AsyncSession) -> AnkiSettings:
        """Fetch the singleton settings row, creating it if absent."""
        result = await session.execute(sa.select(AnkiSettings).limit(1))
        settings = result.scalar_one_or_none()
        if settings is None:
            settings = AnkiSettings(anki_connect_url=None)
            session.add(settings)
            await session.flush()
        return settings

    async def update_url(
        self, session: AsyncSession, url: Optional[str]
    ) -> AnkiSettings:
        settings = await self.get_settings(session)
        settings.anki_connect_url = url
        await session.flush()
        return settings

    async def get_pending_words(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
    ) -> list[Word]:
        """Return all words with anki_pending=true for this user+language."""
        result = await session.execute(
            sa.select(Word).where(
                Word.user_id == user_id,
                Word.language_id == language_id,
                Word.anki_pending.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_learning_words(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
    ) -> list[Word]:
        """Return all 'learning' status words for this user+language."""
        result = await session.execute(
            sa.select(Word).where(
                Word.user_id == user_id,
                Word.language_id == language_id,
                Word.status == "learning",
            )
        )
        return list(result.scalars().all())

    async def mark_pending(
        self,
        session: AsyncSession,
        word_ids: list[uuid.UUID],
    ) -> None:
        """Mark words as pending Anki sync."""
        if not word_ids:
            return
        await session.execute(
            sa.update(Word)
            .where(Word.id.in_(word_ids))
            .values(anki_pending=True)
        )

    async def clear_pending(
        self,
        session: AsyncSession,
        word_ids: list[uuid.UUID],
    ) -> None:
        """Clear anki_pending flag after successful sync."""
        if not word_ids:
            return
        await session.execute(
            sa.update(Word)
            .where(Word.id.in_(word_ids))
            .values(anki_pending=False)
        )

    async def get_pending_count(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
    ) -> int:
        result = await session.execute(
            sa.select(sa.func.count()).where(
                Word.user_id == user_id,
                Word.language_id == language_id,
                Word.anki_pending.is_(True),
            )
        )
        return result.scalar_one()
