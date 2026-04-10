from __future__ import annotations

import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.providers import Provider


class ProviderRepository:
    async def list_all(
        self, session: AsyncSession, type_filter: Optional[str] = None
    ) -> list[Provider]:
        query = sa.select(Provider).order_by(Provider.type, Provider.slug)
        if type_filter:
            query = query.where(Provider.type == type_filter)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def find_by_id(
        self, session: AsyncSession, provider_id: uuid.UUID
    ) -> Provider | None:
        result = await session.execute(
            sa.select(Provider).where(Provider.id == provider_id)
        )
        return result.scalar_one_or_none()

    async def find_by_slug(
        self, session: AsyncSession, slug: str, type_filter: Optional[str] = None
    ) -> Provider | None:
        query = sa.select(Provider).where(Provider.slug == slug)
        if type_filter:
            query = query.where(Provider.type == type_filter)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def list_active_by_type(
        self, session: AsyncSession, type_filter: str
    ) -> list[Provider]:
        """Return all is_active providers of the given type."""
        result = await session.execute(
            sa.select(Provider)
            .where(Provider.type == type_filter, Provider.is_active.is_(True))
            .order_by(Provider.slug)
        )
        return list(result.scalars().all())

    async def list_user_active_by_type(
        self, session: AsyncSession, user_id: uuid.UUID, type_filter: str
    ) -> list[Provider]:
        """Return active providers of the given type that the user can use.

        A provider is usable if it is builtin (system-level) OR the user has
        stored an API key for it.
        """
        from src.infrastructure.db.models.user_api_keys import UserApiKey  # avoid circular

        result = await session.execute(
            sa.select(Provider)
            .outerjoin(
                UserApiKey,
                sa.and_(
                    UserApiKey.provider_id == Provider.id,
                    UserApiKey.user_id == user_id,
                ),
            )
            .where(
                Provider.type == type_filter,
                Provider.is_active.is_(True),
                sa.or_(Provider.is_builtin.is_(True), UserApiKey.id.is_not(None)),
            )
            .order_by(Provider.slug)
        )
        return list(result.scalars().all())

    async def update(
        self,
        session: AsyncSession,
        provider_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> Provider | None:
        provider = await self.find_by_id(session, provider_id)
        if not provider:
            return None
        if name is not None:
            provider.name = name
        if description is not None:
            provider.description = description
        if is_active is not None:
            provider.is_active = is_active
        await session.flush()
        return provider
