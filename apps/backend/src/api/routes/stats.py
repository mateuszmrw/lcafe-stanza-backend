import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.users import User
from src.infrastructure.db.models.word_frequencies import WordFrequency
from src.infrastructure.db.models.words import Word

router = APIRouter(prefix="/stats", tags=["stats"])

_CACHE_TTL = 300  # 5 minutes


class KnownOverTimePoint(BaseModel):
    date: str
    known_cumulative: int


class FrequencyCoverage(BaseModel):
    top_1k: float | None
    top_5k: float | None
    top_10k: float | None


class StatsResponse(BaseModel):
    language_code: str
    word_counts: dict[str, int]
    known_over_time: list[KnownOverTimePoint]
    frequency_coverage: FrequencyCoverage
    books_total: int
    pages_read: int


@router.get("/{language_code}", response_model=StatsResponse)
async def get_stats(
    language_code: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> StatsResponse:
    cache_key = f"stats:{current_user.id}:{language_code}"
    cached = await redis.get(cache_key)
    if cached:
        return StatsResponse.model_validate_json(cached)

    lang_result = await session.execute(
        sa.select(Language.id).where(Language.code == language_code)
    )
    lang_row = lang_result.one_or_none()
    if not lang_row:
        raise HTTPException(status_code=404, detail=f"Language '{language_code}' not found")
    language_id: int = lang_row[0]

    # Word counts by status
    counts_result = await session.execute(
        sa.select(Word.status, sa.func.count().label("cnt"))
        .where(Word.user_id == current_user.id, Word.language_id == language_id)
        .group_by(Word.status)
    )
    word_counts: dict[str, int] = {row.status: row.cnt for row in counts_result}

    # Known words over time (cumulative)
    day_expr = sa.func.date_trunc("day", Word.created_at).label("day")
    known_over_time_result = await session.execute(
        sa.select(
            day_expr,
            sa.func.sum(sa.func.count())
            .over(order_by=day_expr)
            .label("known_cumulative"),
        )
        .where(
            Word.user_id == current_user.id,
            Word.language_id == language_id,
            Word.status.in_(["known", "well_known"]),
        )
        .group_by(day_expr)
        .order_by(day_expr)
    )
    known_over_time = [
        KnownOverTimePoint(
            date=str(row.day.date()) if hasattr(row.day, "date") else str(row.day)[:10],
            known_cumulative=int(row.known_cumulative),
        )
        for row in known_over_time_result
    ]

    # Frequency coverage — check if any freq data exists for this language
    freq_exists = await session.scalar(
        sa.select(sa.func.count())
        .select_from(WordFrequency)
        .where(WordFrequency.language_code == language_code)
        .limit(1)
    )

    if freq_exists:
        async def _tier_coverage(tier_size: int) -> float | None:
            """Return fraction of the top-N most frequent words the user knows,
            where N is the actual number of entries in the frequency table for
            this language capped at tier_size. Returns None if the table has
            no entries in that tier.
            """
            # Actual number of distinct lemmas in this tier (may be < tier_size
            # if the imported frequency list is short).
            total = await session.scalar(
                sa.select(sa.func.count())
                .select_from(WordFrequency)
                .where(
                    WordFrequency.language_code == language_code,
                    WordFrequency.rank <= tier_size,
                )
            ) or 0
            if total == 0:
                return None

            known = await session.scalar(
                sa.select(sa.func.count())
                .select_from(Word)
                .join(
                    WordFrequency,
                    sa.and_(
                        WordFrequency.lemma == Word.lemma,
                        WordFrequency.language_code == language_code,
                        WordFrequency.rank <= tier_size,
                    ),
                )
                .where(
                    Word.user_id == current_user.id,
                    Word.language_id == language_id,
                    Word.status.in_(["known", "well_known"]),
                )
            ) or 0

            return round(min(known / total, 1.0), 4)

        frequency_coverage = FrequencyCoverage(
            top_1k=await _tier_coverage(1000),
            top_5k=await _tier_coverage(5000),
            top_10k=await _tier_coverage(10000),
        )
    else:
        frequency_coverage = FrequencyCoverage(top_1k=None, top_5k=None, top_10k=None)

    # Books total
    books_total = await session.scalar(
        sa.select(sa.func.count())
        .select_from(ContentItem)
        .where(
            ContentItem.user_id == current_user.id,
            ContentItem.language_id == language_id,
            ContentItem.type == "book",
        )
    ) or 0

    # Pages read (tokenized pages)
    pages_read = await session.scalar(
        sa.select(sa.func.count())
        .select_from(ContentPage)
        .join(ContentItem, ContentItem.id == ContentPage.content_item_id)
        .where(
            ContentItem.user_id == current_user.id,
            ContentItem.language_id == language_id,
            ContentPage.status == "ready",
        )
    ) or 0

    response = StatsResponse(
        language_code=language_code,
        word_counts=word_counts,
        known_over_time=known_over_time,
        frequency_coverage=frequency_coverage,
        books_total=books_total,
        pages_read=pages_read,
    )

    await redis.setex(cache_key, _CACHE_TTL, response.model_dump_json())
    return response
