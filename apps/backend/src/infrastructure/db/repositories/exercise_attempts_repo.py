from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.exercises import ExerciseAttempt


class ExerciseAttemptsRepository:
    async def batch_insert(
        self,
        session: AsyncSession,
        attempts: list[dict],
    ) -> None:
        """Insert multiple exercise attempts in a single batch.

        Args:
            session: AsyncSession for DB access.
            attempts: List of dicts with keys:
                - user_id (UUID)
                - word_id (UUID)
                - content_item_id (UUID)
                - exercise_type (str)
                - correct (bool)
        """
        if not attempts:
            return

        # Batch insert at a reasonable size to avoid hitting PostgreSQL bind parameter limits
        batch_size = 1000
        for i in range(0, len(attempts), batch_size):
            batch = attempts[i : i + batch_size]
            await session.execute(
                sa.insert(ExerciseAttempt).values(batch)
            )

    async def count_correct_rounds_since(
        self,
        session: AsyncSession,
        word_id: uuid.UUID,
        user_id: uuid.UUID,
        since_round_start: datetime,
    ) -> int:
        """Count correct exercise attempts for a word since a given timestamp.

        Args:
            session: AsyncSession for DB access.
            word_id: UUID of the word.
            user_id: UUID of the user.
            since_round_start: Datetime to count from (inclusive).

        Returns:
            Count of correct attempts.
        """
        result = await session.execute(
            sa.select(sa.func.count(ExerciseAttempt.id)).where(
                ExerciseAttempt.word_id == word_id,
                ExerciseAttempt.user_id == user_id,
                ExerciseAttempt.correct is True,
                ExerciseAttempt.created_at >= since_round_start,
            )
        )
        return result.scalar() or 0
