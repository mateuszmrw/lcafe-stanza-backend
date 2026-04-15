from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.cc_cedict import CcCedictEntry


class CcCedictRepository:
    async def lookup(self, session: AsyncSession, word: str) -> list[CcCedictEntry]:
        """Match on simplified OR traditional Chinese."""
        result = await session.execute(
            sa.select(CcCedictEntry).where(
                sa.or_(
                    CcCedictEntry.simplified == word,
                    CcCedictEntry.traditional == word,
                )
            )
        )
        return list(result.scalars().all())

    async def bulk_insert(self, session: AsyncSession, rows: list[dict]) -> int:
        if not rows:
            return 0
        for row in rows:
            row.setdefault("id", uuid.uuid4())
        await session.execute(sa.insert(CcCedictEntry), rows)
        return len(rows)

    async def delete_all(self, session: AsyncSession) -> int:
        result = await session.execute(sa.delete(CcCedictEntry))
        return result.rowcount  # type: ignore[return-value]

    async def count(self, session: AsyncSession) -> int:
        result = await session.scalar(
            sa.select(sa.func.count()).select_from(CcCedictEntry)
        )
        return result or 0
