from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.openrussian import OpenRussianWord


class OpenRussianRepository:
    async def lookup(self, session: AsyncSession, word: str) -> list[OpenRussianWord]:
        result = await session.execute(
            sa.select(OpenRussianWord).where(OpenRussianWord.bare == word.lower())
        )
        return list(result.scalars().all())

    async def bulk_insert(self, session: AsyncSession, rows: list[dict]) -> int:
        if not rows:
            return 0
        for row in rows:
            row.setdefault("id", uuid.uuid4())
        await session.execute(sa.insert(OpenRussianWord), rows)
        return len(rows)

    async def delete_all(self, session: AsyncSession) -> int:
        result = await session.execute(sa.delete(OpenRussianWord))
        return result.rowcount  # type: ignore[return-value]

    async def delete_pair(
        self, session: AsyncSession, source_lang: str, target_lang: str
    ) -> int:
        """OpenRussian is ru→en only — delete all entries for any pair involving ru."""
        if source_lang == "ru":
            return await self.delete_all(session)
        return 0

    async def count(self, session: AsyncSession) -> int:
        result = await session.scalar(
            sa.select(sa.func.count()).select_from(OpenRussianWord)
        )
        return result or 0
