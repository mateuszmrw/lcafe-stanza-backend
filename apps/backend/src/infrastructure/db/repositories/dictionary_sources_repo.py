from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.dictionary_sources import DictionarySource


class DictionarySourcesRepository:
    async def list_active(self, session: AsyncSession) -> list[DictionarySource]:
        result = await session.execute(
            sa.select(DictionarySource)
            .where(DictionarySource.is_active.is_(True))
            .order_by(DictionarySource.priority.desc(), DictionarySource.slug)
        )
        return list(result.scalars().all())

    async def list_all(self, session: AsyncSession) -> list[DictionarySource]:
        result = await session.execute(
            sa.select(DictionarySource).order_by(
                DictionarySource.priority.desc(), DictionarySource.slug
            )
        )
        return list(result.scalars().all())

    async def get_by_slug(
        self, session: AsyncSession, slug: str
    ) -> DictionarySource | None:
        result = await session.execute(
            sa.select(DictionarySource).where(DictionarySource.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        slug: str,
        name: str,
        description: str | None = None,
        supported_pairs: list[dict] | None = None,
        priority: int = 5,
    ) -> DictionarySource:
        source = DictionarySource(
            id=uuid.uuid4(),
            slug=slug,
            name=name,
            description=description,
            supported_pairs=supported_pairs or [],
            priority=priority,
            is_active=True,
        )
        session.add(source)
        await session.flush()
        return source

    async def update(
        self,
        session: AsyncSession,
        slug: str,
        priority: int | None = None,
        is_active: bool | None = None,
        name: str | None = None,
        description: str | None = None,
        supported_pairs: list[dict] | None = None,
    ) -> DictionarySource | None:
        source = await self.get_by_slug(session, slug)
        if not source:
            return None
        if priority is not None:
            source.priority = priority
        if is_active is not None:
            source.is_active = is_active
        if name is not None:
            source.name = name
        if description is not None:
            source.description = description
        if supported_pairs is not None:
            source.supported_pairs = supported_pairs
        source.updated_at = datetime.now(tz=timezone.utc)
        await session.flush()
        return source

    async def delete(self, session: AsyncSession, slug: str) -> bool:
        source = await self.get_by_slug(session, slug)
        if not source:
            return False
        await session.delete(source)
        await session.flush()
        return True
