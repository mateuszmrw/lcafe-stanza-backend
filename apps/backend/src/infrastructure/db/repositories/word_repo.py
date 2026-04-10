from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.words import Word


class WordRepository:
    async def bulk_upsert(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        rows: list[dict],
    ) -> None:
        """Insert new words; skip existing ones (preserves current status)."""
        if not rows:
            return
        # PostgreSQL limit is 65,535 bind parameters. Word has 7 columns,
        # so batch at 1,000 rows (7,000 params) to stay well under the limit.
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            stmt = (
                pg_insert(Word)
                .values(batch)
                .on_conflict_do_nothing(
                    index_elements=["user_id", "language_id", "word"]
                )
            )
            await session.execute(stmt)

    async def get_words_map(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        words: list[str],
    ) -> dict[str, dict]:
        """Return {word: {id, lemma, pos, reading, gender, status}} for the given surface forms."""
        if not words:
            return {}
        result = await session.execute(
            sa.select(Word.id, Word.word, Word.lemma, Word.pos, Word.reading, Word.gender, Word.feats, Word.dep_head, Word.dep_rel, Word.status).where(
                Word.user_id == user_id,
                Word.language_id == language_id,
                Word.word.in_(words),
            )
        )
        return {
            row.word: {
                "id": str(row.id),
                "lemma": row.lemma,
                "pos": row.pos,
                "reading": row.reading,
                "gender": row.gender,
                "feats": row.feats,
                "dep_head": row.dep_head,
                "dep_rel": row.dep_rel,
                "status": row.status,
            }
            for row in result
        }

    async def list_paginated(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        status: str | None = None,
        pos: str | None = None,
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
        if pos:
            query = query.where(Word.pos == pos)

        total_result = await session.execute(
            sa.select(sa.func.count()).select_from(query.subquery())
        )
        total = total_result.scalar_one()

        result = await session.execute(query.offset((page - 1) * limit).limit(limit))
        return list(result.scalars().all()), total

    async def bulk_update_status(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        ids: list[uuid.UUID],
        status: str,
    ) -> int:
        """Update status for multiple words owned by the user. Returns affected count."""
        if not ids:
            return 0
        result = await session.execute(
            sa.update(Word)
            .where(Word.user_id == user_id, Word.id.in_(ids))
            .values(status=status)
        )
        return result.rowcount  # type: ignore[return-value]

    async def find_by_id(
        self, session: AsyncSession, word_id: uuid.UUID
    ) -> Word | None:
        result = await session.execute(sa.select(Word).where(Word.id == word_id))
        return result.scalar_one_or_none()

    async def update_status(
        self, session: AsyncSession, word_id: uuid.UUID, status: str
    ) -> Word | None:
        word = await self.find_by_id(session, word_id)
        if not word:
            return None
        word.status = status
        await session.flush()
        return word

    async def batch_upsert_status(
        self,
        session: AsyncSession,
        rows: list[dict],
    ) -> None:
        """Insert-or-update status for multiple words in a single statement.

        Each dict must have: user_id, language_id, word, status,
        and optionally lemma, pos, reading, gender, feats.
        """
        if not rows:
            return
        for row in rows:
            row.setdefault("lemma", "")
            row.setdefault("pos", "")
            row.setdefault("reading", "")
            row.setdefault("gender", "")
            row.setdefault("feats", "")
            row.setdefault("dep_head", 0)
            row.setdefault("dep_rel", "")
        stmt = (
            pg_insert(Word)
            .values(rows)
            .on_conflict_do_update(
                index_elements=["user_id", "language_id", "word"],
                set_={"status": sa.text("excluded.status")},
            )
        )
        await session.execute(stmt)

    async def upsert_with_status(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        word: str,
        status: str,
        lemma: str = "",
        pos: str = "",
        reading: str = "",
        gender: str = "",
        feats: str = "",
    ) -> Word:
        """Insert word if new, update status on conflict. Returns the word row."""
        stmt = (
            pg_insert(Word)
            .values(
                user_id=user_id,
                language_id=language_id,
                word=word.lower().strip(),
                lemma=lemma,
                pos=pos,
                reading=reading,
                gender=gender,
                feats=feats,
                status=status,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "language_id", "word"],
                set_={"status": status},
            )
            .returning(Word)
        )
        result = await session.execute(stmt)
        return result.scalar_one()
