from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.activity import DailyActivity


class DailyActivityRepository:
    async def record_page(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        today: date,
    ) -> None:
        """Upsert today's activity row, incrementing pages_read by 1."""
        stmt = (
            pg_insert(DailyActivity)
            .values(user_id=user_id, language_id=language_id, date=today, pages_read=1)
            .on_conflict_do_update(
                index_elements=["user_id", "language_id", "date"],
                set_={"pages_read": DailyActivity.pages_read + 1},
            )
        )
        await session.execute(stmt)

    async def get_streak(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
    ) -> tuple[int, int]:
        """Return (current_streak, longest_streak) in days.

        Current streak = consecutive days of activity ending today or yesterday
        (yesterday counts so the streak doesn't reset until the user misses a full day).
        Longest streak = longest run of consecutive active days ever recorded.
        """
        result = await session.execute(
            sa.select(DailyActivity.date)
            .where(
                DailyActivity.user_id == user_id,
                DailyActivity.language_id == language_id,
            )
            .order_by(DailyActivity.date.desc())
        )
        # Distinct, sorted descending — most recent first.
        dates = [row[0] for row in result.fetchall()]
        if not dates:
            return 0, 0

        today = date.today()
        yesterday = today - timedelta(days=1)

        # Current streak: only alive if the most recent activity was today or yesterday.
        current = 0
        if dates[0] == today or dates[0] == yesterday:
            current = 1
            for i in range(1, len(dates)):
                if dates[i - 1] - dates[i] == timedelta(days=1):
                    current += 1
                else:
                    break

        # Longest streak: walk the full list counting consecutive runs.
        longest = 1
        run = 1
        for i in range(1, len(dates)):
            if dates[i - 1] - dates[i] == timedelta(days=1):
                run += 1
                longest = max(longest, run)
            else:
                run = 1

        return current, longest

    async def get_calendar(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        days: int = 365,
    ) -> list[dict[str, Any]]:
        """Return [{date: 'YYYY-MM-DD', pages: N}, ...] for the past N days (only active days)."""
        cutoff = date.today() - timedelta(days=days - 1)
        result = await session.execute(
            sa.select(DailyActivity.date, DailyActivity.pages_read).where(
                DailyActivity.user_id == user_id,
                DailyActivity.language_id == language_id,
                DailyActivity.date >= cutoff,
            ).order_by(DailyActivity.date)
        )
        return [{"date": row.date.isoformat(), "pages": row.pages_read} for row in result]
