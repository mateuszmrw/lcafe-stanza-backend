from fastapi import HTTPException
from redis.asyncio import Redis


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise HTTP 429 if the given Redis key has been incremented more than `limit` times
    within the last `window_seconds`.

    Uses a simple counter with TTL — not a sliding window, but sufficient for
    coarse rate limiting (e.g. 3 LLM requests per minute per user).
    """
    count = await redis.incr(key)
    if count == 1:
        # First request in this window — set expiry now.
        await redis.expire(key, window_seconds)
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {limit} requests per {window_seconds}s.",
        )
