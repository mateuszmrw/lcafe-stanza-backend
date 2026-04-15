from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.users import UserLanguageProfile


class UserLanguageProfileRepository:
    async def find_by_user_and_language(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
    ) -> UserLanguageProfile | None:
        """Return the language profile for a specific user/language pair, or None."""
        result = await session.execute(
            sa.select(UserLanguageProfile).where(
                UserLanguageProfile.user_id == user_id,
                UserLanguageProfile.language_id == language_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        **fields: Any,
    ) -> None:
        """Insert or update a language profile for the given user/language pair.

        Only the fields passed as keyword arguments are written. No-op if fields is empty.
        """
        if not fields:
            return
        insert_values = {"user_id": user_id, "language_id": language_id, **fields}
        await session.execute(
            pg.insert(UserLanguageProfile)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=["user_id", "language_id"],
                set_=fields,
            )
        )
