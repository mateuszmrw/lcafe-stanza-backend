import logging

from fastapi import HTTPException
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise HTTP 429 if the given Redis key has been incremented more than
    `limit` times within the last `window_seconds`.

    Uses a simple counter with TTL — not a sliding window, but sufficient for
    coarse rate limiting (e.g. 3 LLM requests per minute per user).

    **Fails closed:** if Redis is unavailable, we raise 503 rather than let
    the caller through. This prevents unlimited LLM spend or auth brute-force
    during a Redis outage.
    """
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
    except RedisError:
        logger.exception("Rate limit check failed — Redis unavailable for key=%s", key)
        raise HTTPException(
            status_code=503,
            detail="Rate limit service temporarily unavailable. Please try again.",
        )

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {limit} requests per {window_seconds}s.",
        )
