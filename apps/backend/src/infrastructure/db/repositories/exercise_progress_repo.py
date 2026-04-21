from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.exercises import ExerciseProgress


class ExerciseProgressRepository:
    async def get_or_create(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        content_item_id: uuid.UUID,
    ) -> ExerciseProgress:
        """Get existing exercise progress or create a new one with defaults."""
        stmt = pg_insert(ExerciseProgress).values(
            user_id=user_id,
            content_item_id=content_item_id,
            last_exercise_page=0,
            snooze_until_page=None,
        ).on_conflict_do_nothing()
        await session.execute(stmt)

        # Now fetch it
        result = await session.execute(
            sa.select(ExerciseProgress).where(
                ExerciseProgress.user_id == user_id,
                ExerciseProgress.content_item_id == content_item_id,
            )
        )
        return result.scalar_one()

    async def update_last_exercise_page(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        content_item_id: uuid.UUID,
        page: int,
    ) -> None:
        """Update last_exercise_page for a user + content item."""
        stmt = (
            sa.update(ExerciseProgress)
            .where(
                ExerciseProgress.user_id == user_id,
                ExerciseProgress.content_item_id == content_item_id,
            )
            .values(last_exercise_page=page)
        )
        await session.execute(stmt)

    async def set_snooze(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        content_item_id: uuid.UUID,
        snooze_until_page: int,
    ) -> None:
        """Set snooze_until_page for a user + content item."""
        stmt = (
            sa.update(ExerciseProgress)
            .where(
                ExerciseProgress.user_id == user_id,
                ExerciseProgress.content_item_id == content_item_id,
            )
            .values(snooze_until_page=snooze_until_page)
        )
        await session.execute(stmt)

    async def clear_snooze(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        content_item_id: uuid.UUID,
    ) -> None:
        """Clear snooze (set to None) for a user + content item."""
        stmt = (
            sa.update(ExerciseProgress)
            .where(
                ExerciseProgress.user_id == user_id,
                ExerciseProgress.content_item_id == content_item_id,
            )
            .values(snooze_until_page=None)
        )
        await session.execute(stmt)
