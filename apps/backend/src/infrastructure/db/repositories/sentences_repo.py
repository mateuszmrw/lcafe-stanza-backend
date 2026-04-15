from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.sentences import SavedSentence


class SavedSentenceRepository:
    async def create(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        sentence_text: str,
        sentence_index: int,
        book_id: uuid.UUID | None = None,
    ) -> SavedSentence:
        sentence = SavedSentence(
            user_id=user_id,
            language_id=language_id,
            sentence_text=sentence_text,
            sentence_index=sentence_index,
            book_id=book_id,
        )
        session.add(sentence)
        await session.flush()
        return sentence

    async def list_by_language(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
    ) -> list[SavedSentence]:
        result = await session.execute(
            sa.select(SavedSentence)
            .where(
                SavedSentence.user_id == user_id,
                SavedSentence.language_id == language_id,
            )
            .order_by(SavedSentence.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_by_id(
        self, session: AsyncSession, sentence_id: uuid.UUID
    ) -> SavedSentence | None:
        result = await session.execute(
            sa.select(SavedSentence).where(SavedSentence.id == sentence_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, session: AsyncSession, sentence_id: uuid.UUID) -> None:
        await session.execute(
            sa.delete(SavedSentence).where(SavedSentence.id == sentence_id)
        )
