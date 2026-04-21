"""Book vocabulary coverage calculation with Redis caching."""
from __future__ import annotations

import logging
import uuid

import sqlalchemy as sa
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 minutes


class CoverageService:
    async def compute_book_coverages(
        self,
        session: AsyncSession,
        redis: Redis | None,
        user_id: uuid.UUID,
        language_id: int,
        content_item_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """Return {content_item_id: (coverage_pct, mastered_pct)} for the given books.

        Checks Redis cache first, computes missing via SQL, caches results.
        Cached value is stored as "coverage,mastered" to stay printable and
        backwards-decodable.
        """
        if not content_item_ids:
            return {}

        result: dict[uuid.UUID, tuple[int, int]] = {}
        to_compute: list[uuid.UUID] = []

        # Check cache
        if redis:
            for cid in content_item_ids:
                cached = await redis.get(f"coverage:{user_id}:{cid}")
                if cached is None:
                    to_compute.append(cid)
                    continue
                decoded = cached.decode() if isinstance(cached, bytes) else cached
                parts = decoded.split(",")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    result[cid] = (int(parts[0]), int(parts[1]))
                else:
                    # Legacy single-int cache entry — recompute to upgrade.
                    to_compute.append(cid)
        else:
            to_compute = list(content_item_ids)

        # Compute missing
        for cid in to_compute:
            pair = await self._compute_single(session, user_id, language_id, cid)
            if pair is not None:
                result[cid] = pair
                if redis:
                    await redis.setex(
                        f"coverage:{user_id}:{cid}",
                        _CACHE_TTL,
                        f"{pair[0]},{pair[1]}",
                    )

        return result

    async def _compute_single(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        content_item_id: uuid.UUID,
    ) -> tuple[int, int] | None:
        """Compute coverage for a single book.

        Returns (coverage_pct, mastered_pct) where:
          - coverage_pct = % of book lemmas with status known/well_known/learning
          - mastered_pct = % of book lemmas with status well_known (subset of coverage)
        Both are 0-100. Returns None if the book has no lemmas.
        """
        result = await session.execute(
            sa.text("""
                WITH book_lemmas AS (
                    SELECT DISTINCT v AS lemma
                    FROM content_pages cp,
                         jsonb_each_text(cp.lemma_map) AS kv(k, v)
                    WHERE cp.content_item_id = :book_id
                      AND cp.lemma_map IS NOT NULL
                )
                SELECT
                    (SELECT COUNT(*) FROM book_lemmas bl
                     WHERE NOT EXISTS (
                         SELECT 1 FROM words w
                         WHERE w.word = bl.lemma
                           AND w.user_id = :user_id
                           AND w.language_id = :language_id
                           AND w.skip_in_vocabulary = TRUE
                     )
                    ) AS total,
                    (SELECT COUNT(*) FROM book_lemmas bl
                     JOIN words w ON w.word = bl.lemma
                       AND w.user_id = :user_id
                       AND w.language_id = :language_id
                       AND w.status IN ('known', 'well_known', 'learning')
                       AND w.skip_in_vocabulary = FALSE
                    ) AS known,
                    (SELECT COUNT(*) FROM book_lemmas bl
                     JOIN words w ON w.word = bl.lemma
                       AND w.user_id = :user_id
                       AND w.language_id = :language_id
                       AND w.status = 'well_known'
                       AND w.skip_in_vocabulary = FALSE
                    ) AS mastered
            """),
            {
                "book_id": content_item_id,
                "user_id": user_id,
                "language_id": language_id,
            },
        )
        row = result.one()
        total = row.total or 0
        known = row.known or 0
        mastered = row.mastered or 0

        if total == 0:
            return None

        return (round(known / total * 100), round(mastered / total * 100))


async def invalidate_coverage_cache(redis: Redis, user_id: uuid.UUID) -> None:
    """Delete all cached coverage entries for this user."""
    pattern = f"coverage:{user_id}:*"
    async for key in redis.scan_iter(pattern):
        await redis.delete(key)
