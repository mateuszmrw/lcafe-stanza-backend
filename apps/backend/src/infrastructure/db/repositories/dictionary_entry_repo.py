from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.dictionary_entries import DictionaryEntry


class DictionaryEntryRepository:
    async def lookup(
        self, session: AsyncSession, word: str, source_lang: str, target_lang: str
    ) -> list[DictionaryEntry]:
        result = await session.execute(
            sa.select(DictionaryEntry).where(
                DictionaryEntry.word == word,
                DictionaryEntry.source_lang == source_lang,
                DictionaryEntry.target_lang == target_lang,
            )
        )
        return list(result.scalars().all())

    async def list_language_pairs(
        self, session: AsyncSession
    ) -> list[tuple[str, str, int]]:
        """Return (source_lang, target_lang, count) tuples for all loaded pairs."""
        result = await session.execute(
            sa.select(
                DictionaryEntry.source_lang,
                DictionaryEntry.target_lang,
                sa.func.count().label("cnt"),
            )
            .group_by(DictionaryEntry.source_lang, DictionaryEntry.target_lang)
            .order_by(DictionaryEntry.source_lang, DictionaryEntry.target_lang)
        )
        return [(row.source_lang, row.target_lang, row.cnt) for row in result.all()]

    async def has_entries(
        self, session: AsyncSession, source_lang: str, target_lang: str
    ) -> bool:
        result = await session.scalar(
            sa.select(sa.func.count()).select_from(DictionaryEntry).where(
                DictionaryEntry.source_lang == source_lang,
                DictionaryEntry.target_lang == target_lang,
            )
        )
        return (result or 0) > 0

    async def delete_pair(
        self, session: AsyncSession, source_lang: str, target_lang: str
    ) -> int:
        result = await session.execute(
            sa.delete(DictionaryEntry).where(
                DictionaryEntry.source_lang == source_lang,
                DictionaryEntry.target_lang == target_lang,
            )
        )
        return result.rowcount  # type: ignore[return-value]

    async def bulk_insert(self, session: AsyncSession, rows: list[dict]) -> int:
        if not rows:
            return 0
        await session.execute(sa.insert(DictionaryEntry), rows)
        return len(rows)

    async def delete_by_source_dict(
        self, session: AsyncSession, source_dict: str
    ) -> int:
        """Delete all entries belonging to a given dictionary source."""
        result = await session.execute(
            sa.delete(DictionaryEntry).where(
                DictionaryEntry.source_dict == source_dict
            )
        )
        return result.rowcount  # type: ignore[return-value]

    async def count_by_source_dict(
        self, session: AsyncSession, source_dict: str
    ) -> int:
        result = await session.scalar(
            sa.select(sa.func.count()).select_from(DictionaryEntry).where(
                DictionaryEntry.source_dict == source_dict
            )
        )
        return result or 0
