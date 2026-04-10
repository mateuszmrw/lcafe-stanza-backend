from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.word_frequencies import WordFrequency


class WordFrequencyRepository:
    async def lookup(
        self, session: AsyncSession, language_code: str, lemma: str
    ) -> WordFrequency | None:
        return await session.scalar(
            sa.select(WordFrequency).where(
                WordFrequency.language_code == language_code,
                WordFrequency.lemma == lemma,
            )
        )

    async def bulk_upsert(self, session: AsyncSession, rows: list[dict]) -> int:
        if not rows:
            return 0
        stmt = pg_insert(WordFrequency).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_freq_language_lemma",
            set_={"rank": stmt.excluded.rank, "per_million": stmt.excluded.per_million},
        )
        await session.execute(stmt)
        return len(rows)

    async def delete_language(self, session: AsyncSession, language_code: str) -> int:
        result = await session.execute(
            sa.delete(WordFrequency).where(WordFrequency.language_code == language_code)
        )
        return result.rowcount  # type: ignore[return-value]

    async def has_entries(self, session: AsyncSession, language_code: str) -> bool:
        count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(WordFrequency)
            .where(WordFrequency.language_code == language_code)
        )
        return (count or 0) > 0
