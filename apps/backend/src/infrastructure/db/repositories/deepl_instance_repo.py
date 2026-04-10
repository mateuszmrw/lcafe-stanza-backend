import uuid
from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.deepl_instances import DeepLInstance


class DeepLInstanceRepository:
    async def list_all(self, session: AsyncSession) -> Sequence[DeepLInstance]:
        result = await session.execute(
            sa.select(DeepLInstance).order_by(DeepLInstance.source_lang, DeepLInstance.target_lang)
        )
        return result.scalars().all()

    async def list_enabled_for_source(
        self, session: AsyncSession, source_lang: str
    ) -> Sequence[DeepLInstance]:
        result = await session.execute(
            sa.select(DeepLInstance).where(
                DeepLInstance.source_lang == source_lang.upper(),
                DeepLInstance.enabled.is_(True),
            )
        )
        return result.scalars().all()

    async def create(
        self, session: AsyncSession, source_lang: str, target_lang: str
    ) -> DeepLInstance:
        instance = DeepLInstance(
            id=uuid.uuid4(),
            source_lang=source_lang.upper(),
            target_lang=target_lang.upper(),
            enabled=True,
        )
        session.add(instance)
        return instance

    async def find_by_id(
        self, session: AsyncSession, instance_id: uuid.UUID
    ) -> DeepLInstance | None:
        result = await session.execute(
            sa.select(DeepLInstance).where(DeepLInstance.id == instance_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, session: AsyncSession, instance_id: uuid.UUID) -> bool:
        result = await session.execute(
            sa.delete(DeepLInstance).where(DeepLInstance.id == instance_id)
        )
        return result.rowcount > 0

    async def toggle_enabled(
        self, session: AsyncSession, instance_id: uuid.UUID, enabled: bool
    ) -> DeepLInstance | None:
        result = await session.execute(
            sa.update(DeepLInstance)
            .where(DeepLInstance.id == instance_id)
            .values(enabled=enabled)
            .returning(DeepLInstance)
        )
        return result.scalar_one_or_none()
