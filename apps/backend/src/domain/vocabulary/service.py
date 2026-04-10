from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.nlp.models.token import Token
from src.infrastructure.db.models.words import Word


class VocabularyService:
    async def list(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        status: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[Word], int]:
        query = (
            sa.select(Word)
            .where(Word.user_id == user_id, Word.language_id == language_id)
            .order_by(Word.created_at.desc())
        )
        if status:
            query = query.where(Word.status == status)

        total_result = await session.execute(
            sa.select(sa.func.count()).select_from(query.subquery())
        )
        total = total_result.scalar_one()

        result = await session.execute(query.offset((page - 1) * limit).limit(limit))
        return result.scalars().all(), total

    async def get_by_id(
        self, session: AsyncSession, word_id: uuid.UUID
    ) -> Word | None:
        result = await session.execute(sa.select(Word).where(Word.id == word_id))
        return result.scalar_one_or_none()

    async def update_status(
        self, session: AsyncSession, word_id: uuid.UUID, status: str
    ) -> Word:
        word = await self.get_by_id(session, word_id)
        if not word:
            raise ValueError(f"Word not found: {word_id}")
        word.status = status
        await session.flush()
        return word

    async def bulk_upsert_from_tokens(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        tokens: list[Token],
    ) -> None:
        """Insert new surface words; skip any that the user already has a status for."""
        rows = [
            {
                "user_id": user_id,
                "language_id": language_id,
                "word": t.w.lower(),
                "lemma": t.l or "",
                "pos": t.pos or "",
                "reading": t.r or "",
            }
            for t in tokens
            if t.w.strip()
        ]
        if not rows:
            return

        stmt = (
            pg_insert(Word)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["user_id", "language_id", "word"])
        )
        await session.execute(stmt)
