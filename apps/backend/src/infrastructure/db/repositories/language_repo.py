from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.languages import Language, LanguageNlpConfig


class LanguageRepository:
    async def list_all(self, session: AsyncSession) -> list[Language]:
        result = await session.execute(sa.select(Language).order_by(Language.id))
        return list(result.scalars().all())

    async def find_by_id(
        self, session: AsyncSession, language_id: int
    ) -> Language | None:
        result = await session.execute(
            sa.select(Language).where(Language.id == language_id)
        )
        return result.scalar_one_or_none()

    async def find_by_code(
        self, session: AsyncSession, code: str
    ) -> Language | None:
        result = await session.execute(
            sa.select(Language).where(Language.code == code)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        code: str,
        name: str,
        flag_emoji: str | None = None,
    ) -> Language:
        language = Language(code=code, name=name, flag_emoji=flag_emoji)
        session.add(language)
        await session.flush()
        return language

    async def update(
        self,
        session: AsyncSession,
        language_id: int,
        name: str | None = None,
        flag_emoji: str | None = None,
        is_active: bool | None = None,
    ) -> Language | None:
        language = await self.find_by_id(session, language_id)
        if not language:
            return None
        if name is not None:
            language.name = name
        if flag_emoji is not None:
            language.flag_emoji = flag_emoji
        if is_active is not None:
            language.is_active = is_active
        await session.flush()
        return language

    async def get_nlp_config(
        self, session: AsyncSession, language_id: int
    ) -> LanguageNlpConfig | None:
        result = await session.execute(
            sa.select(LanguageNlpConfig).where(
                LanguageNlpConfig.language_id == language_id
            )
        )
        return result.scalar_one_or_none()

    async def set_nlp_config(
        self,
        session: AsyncSession,
        language_id: int,
        provider_id: str,
        config: dict,
    ) -> LanguageNlpConfig:
        existing = await self.get_nlp_config(session, language_id)
        if existing:
            existing.provider_id = provider_id  # type: ignore[assignment]
            existing.config = config
        else:
            existing = LanguageNlpConfig(
                language_id=language_id,
                provider_id=provider_id,  # type: ignore[arg-type]
                config=config,
            )
            session.add(existing)
        await session.flush()
        return existing
