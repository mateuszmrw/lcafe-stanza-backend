from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.dict_cc import DictCcEntry


class DictCcRepository:
    async def lookup(
        self, session: AsyncSession, word: str, source_lang: str, target_lang: str
    ) -> list[DictCcEntry]:
        """Look up entries by source_word for the given language pair."""
        result = await session.execute(
            sa.select(DictCcEntry).where(
                DictCcEntry.source_word == word,
                DictCcEntry.source_lang == source_lang,
                DictCcEntry.target_lang == target_lang,
            )
        )
        return list(result.scalars().all())

    async def bulk_insert(self, session: AsyncSession, rows: list[dict]) -> int:
        if not rows:
            return 0
        for row in rows:
            row.setdefault("id", uuid.uuid4())
        await session.execute(sa.insert(DictCcEntry), rows)
        return len(rows)

    async def delete_all(self, session: AsyncSession) -> int:
        result = await session.execute(sa.delete(DictCcEntry))
        return result.rowcount  # type: ignore[return-value]

    async def count(self, session: AsyncSession) -> int:
        result = await session.scalar(
            sa.select(sa.func.count()).select_from(DictCcEntry)
        )
        return result or 0
