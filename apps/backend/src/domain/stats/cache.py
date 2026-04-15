import uuid

from redis.asyncio import Redis


async def invalidate_stats_cache(redis: Redis, user_id: uuid.UUID) -> None:
    """Delete all cached stats entries for this user (all languages).

    Called whenever vocabulary status changes so that the stats page
    reflects the new counts without waiting for the 5-minute TTL.
    """
    pattern = f"stats:{user_id}:*"
    async for key in redis.scan_iter(pattern):
        await redis.delete(key)
