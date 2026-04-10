from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.phrases import Phrase


class PhraseRepository:
    async def create(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int | None,
        text: str,
        translation: str | None = None,
        context: str | None = None,
        book_id: uuid.UUID | None = None,
        page: int | None = None,
    ) -> Phrase:
        phrase = Phrase(
            user_id=user_id,
            language_id=language_id,
            text=text,
            translation=translation,
            context=context,
            book_id=book_id,
            page=page,
        )
        session.add(phrase)
        await session.flush()
        return phrase

    async def list_paginated(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[Phrase], int]:
        query = (
            sa.select(Phrase)
            .where(Phrase.user_id == user_id)
            .order_by(Phrase.created_at.desc())
        )
        if language_id is not None:
            query = query.where(Phrase.language_id == language_id)
        if status:
            query = query.where(Phrase.status == status)

        total = await session.scalar(
            sa.select(sa.func.count()).select_from(query.subquery())
        )
        result = await session.execute(query.offset((page - 1) * limit).limit(limit))
        return list(result.scalars().all()), total or 0

    async def find_by_id(
        self, session: AsyncSession, phrase_id: uuid.UUID, user_id: uuid.UUID
    ) -> Phrase | None:
        return await session.scalar(
            sa.select(Phrase).where(Phrase.id == phrase_id, Phrase.user_id == user_id)
        )

    async def update_status(
        self, session: AsyncSession, phrase_id: uuid.UUID, user_id: uuid.UUID, status: str
    ) -> Phrase | None:
        phrase = await self.find_by_id(session, phrase_id, user_id)
        if not phrase:
            return None
        phrase.status = status
        await session.flush()
        return phrase

    async def delete(
        self, session: AsyncSession, phrase_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        result = await session.execute(
            sa.delete(Phrase).where(Phrase.id == phrase_id, Phrase.user_id == user_id)
        )
        return result.rowcount > 0  # type: ignore[return-value]
