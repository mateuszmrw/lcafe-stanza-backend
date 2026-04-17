"""Centralised Redis keys and channel names for content import progress."""
from __future__ import annotations

import uuid

from redis.asyncio import Redis

# Redis key templates — use .format(book_id=...) to expand
TOTAL_PAGES_KEY = "book:{book_id}:total_pages"
COMPLETED_PAGES_KEY = "book:{book_id}:completed_pages"
TOKEN_COUNT_KEY = "book:{book_id}:token_count"
FINALIZING_KEY = "book:{book_id}:finalizing"

# Pub/sub channel templates
IMPORT_CHANNEL = "import:{book_id}"
AUDIO_ALIGN_CHANNEL = "audio-align:{book_id}"

_TOTAL_TTL = 86400  # 24 h


async def set_total_pages(
    redis: Redis, book_id: uuid.UUID, total: int, ttl: int = _TOTAL_TTL
) -> None:
    """Store the expected page count at upload time so workers can compute progress."""
    await redis.setex(TOTAL_PAGES_KEY.format(book_id=book_id), ttl, total)
