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
        """Return (current_streak, longest_streak) in days."""
        result = await session.execute(
            sa.select(DailyActivity.date)
            .where(
                DailyActivity.user_id == user_id,
                DailyActivity.language_id == language_id,
            )
            .order_by(DailyActivity.date.desc())
        )
        dates = [row[0] for row in result.fetchall()]

        if not dates:
            return 0, 0

        today = date.today()
        current = 0
        longest = 0
        streak = 0
        prev: date | None = None

        for d in dates:
            if prev is None:
                # Start of iteration — check if today or yesterday to open current streak
                if d >= today - timedelta(days=1):
                    current = 1
                streak = 1
            else:
                if prev - d == timedelta(days=1):
                    streak += 1
                    if d >= today - timedelta(days=1):
                        current = streak
                else:
                    streak = 1
                    if current == 0 and d >= today - timedelta(days=1):
                        current = 1
            longest = max(longest, streak)
            prev = d

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
