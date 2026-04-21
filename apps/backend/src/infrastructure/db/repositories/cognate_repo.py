import logging
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.cognates import CognatePair, CognateLanguagePair

logger = logging.getLogger(__name__)

_VALID_COGNATE_TYPES = frozenset({"true", "false_friend", "partial", "borrowing"})
_BATCH_SIZE = 1000


class CognateRepository:
    async def get_cognate(
        self,
        session: AsyncSession,
        l2_lemma: str,
        l2_language: str,
        l1_language: str,
    ) -> Optional[CognatePair]:
        result = await session.execute(
            sa.select(CognatePair).where(
                CognatePair.l2_lemma == l2_lemma,
                CognatePair.l2_language == l2_language,
                CognatePair.l1_language == l1_language,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def is_pair_supported(
        self,
        session: AsyncSession,
        l2_language: str,
        l1_language: str,
    ) -> bool:
        result = await session.execute(
            sa.select(CognateLanguagePair).where(
                CognateLanguagePair.l2_language == l2_language,
                CognateLanguagePair.supported_l1_codes.contains([l1_language]),
            )
        )
        return result.scalar_one_or_none() is not None

    async def batch_get_cognates(
        self,
        session: AsyncSession,
        l2_lemmas: list[str],
        l2_language: str,
        l1_language: str,
    ) -> dict[str, dict]:
        if not l2_lemmas:
            return {}
        result = await session.execute(
            sa.select(
                CognatePair.l2_lemma,
                CognatePair.cognate_type,
                CognatePair.l1_lemma,
                CognatePair.l1_meaning,
                CognatePair.l2_meaning,
                CognatePair.similarity_score,
            ).where(
                CognatePair.l2_lemma.in_(l2_lemmas),
                CognatePair.l2_language == l2_language,
                CognatePair.l1_language == l1_language,
            )
        )
        return {
            row.l2_lemma: {
                "cognate_type": row.cognate_type,
                "l1_lemma": row.l1_lemma,
                "l1_meaning": row.l1_meaning,
                "l2_meaning": row.l2_meaning,
                "similarity_score": row.similarity_score,
            }
            for row in result
        }

    async def bulk_upsert(self, session: AsyncSession, rows: list[dict]) -> int:
        if not rows:
            return 0
        imported = 0
        for i in range(0, len(rows), _BATCH_SIZE):
            batch = rows[i : i + _BATCH_SIZE]
            stmt = insert(CognatePair).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["l1_lemma", "l1_language", "l2_lemma", "l2_language"],
                set_={
                    "cognate_type": stmt.excluded.cognate_type,
                    "similarity_score": stmt.excluded.similarity_score,
                    "semantic_score": stmt.excluded.semantic_score,
                    "source": stmt.excluded.source,
                    "l1_meaning": stmt.excluded.l1_meaning,
                    "l2_meaning": stmt.excluded.l2_meaning,
                },
            )
            await session.execute(stmt)
            imported += len(batch)
        return imported

    async def mark_imported(self, session: AsyncSession, l2_language: str) -> None:
        await session.execute(
            sa.update(CognateLanguagePair)
            .where(CognateLanguagePair.l2_language == l2_language)
            .values(last_imported_at=datetime.now(timezone.utc))
        )

    async def get_status(self, session: AsyncSession) -> dict:
        count_result = await session.execute(
            sa.select(sa.func.count()).select_from(CognatePair)
        )
        row_count = count_result.scalar_one()

        pairs_result = await session.execute(sa.select(CognateLanguagePair))
        pairs_rows = pairs_result.scalars().all()

        last_imported_at: Optional[datetime] = None
        for p in pairs_rows:
            if p.last_imported_at and (
                last_imported_at is None or p.last_imported_at > last_imported_at
            ):
                last_imported_at = p.last_imported_at

        pairs = [
            {"l2": p.l2_language, "l1_codes": p.supported_l1_codes}
            for p in pairs_rows
        ]

        return {
            "row_count": row_count,
            "last_imported_at": last_imported_at,
            "pairs": pairs,
        }
