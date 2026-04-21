from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.activity_repo import DailyActivityRepository
from src.infrastructure.db.repositories.content_repo import ContentRepository
from src.infrastructure.db.repositories.language_repo import LanguageRepository
from src.infrastructure.db.repositories.word_frequency_repo import (
    WordFrequencyRepository,
)
from src.infrastructure.db.repositories.word_repo import WordRepository

router = APIRouter(prefix="/stats", tags=["stats"])

_CACHE_TTL = 300  # 5 minutes

_language_repo = LanguageRepository()
_word_repo = WordRepository()
_word_freq_repo = WordFrequencyRepository()
_content_repo = ContentRepository()
_activity_repo = DailyActivityRepository()


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

    language = await _language_repo.find_by_code(session, language_code)
    if not language:
        raise HTTPException(
            status_code=404, detail=f"Language '{language_code}' not found"
        )
    language_id = language.id

    word_counts = await _word_repo.count_by_status(
        session, current_user.id, language_id
    )

    known_over_time = [
        KnownOverTimePoint(date=date_str, known_cumulative=count)
        for date_str, count in await _word_repo.known_over_time(
            session, current_user.id, language_id
        )
    ]

    if await _word_freq_repo.has_entries(session, language_code):
        async def _tier_coverage(tier_size: int) -> float | None:
            total = await _word_freq_repo.count_in_tier(
                session, language_code, tier_size
            )
            if total == 0:
                return None
            known = await _word_freq_repo.count_known_in_tier(
                session, current_user.id, language_id, language_code, tier_size
            )
            return round(min(known / total, 1.0), 4)

        frequency_coverage = FrequencyCoverage(
            top_1k=await _tier_coverage(1000),
            top_5k=await _tier_coverage(5000),
            top_10k=await _tier_coverage(10000),
        )
    else:
        frequency_coverage = FrequencyCoverage(top_1k=None, top_5k=None, top_10k=None)

    books_total = await _content_repo.count_books_for_user_language(
        session, current_user.id, language_id
    )
    pages_read = await _activity_repo.sum_pages_read(
        session, current_user.id, language_id
    )

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
