from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.krdict import KrdictEntry


class KrdictRepository:
    async def lookup(self, session: AsyncSession, word: str) -> list[KrdictEntry]:
        result = await session.execute(
            sa.select(KrdictEntry).where(KrdictEntry.word == word)
        )
        return list(result.scalars().all())

    async def bulk_insert(self, session: AsyncSession, rows: list[dict]) -> int:
        if not rows:
            return 0
        for row in rows:
            row.setdefault("id", uuid.uuid4())
        await session.execute(sa.insert(KrdictEntry), rows)
        return len(rows)

    async def delete_all(self, session: AsyncSession) -> int:
        result = await session.execute(sa.delete(KrdictEntry))
        return result.rowcount  # type: ignore[return-value]

    async def count(self, session: AsyncSession) -> int:
        result = await session.scalar(
            sa.select(sa.func.count()).select_from(KrdictEntry)
        )
        return result or 0
