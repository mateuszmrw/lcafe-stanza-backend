"""Fan-out retokenize task for ADR-019 coref toggle.

When a user enables coref for a language, this job enqueues a tokenize_page
job for every page in the user's content items for that language so that
coref chain data is populated in content_pages.tokens.
"""
import logging
import uuid

import sqlalchemy as sa
from redis.asyncio import Redis

from src.infrastructure.db.engine import AsyncSessionFactory
from src.infrastructure.db.models.content import ContentItem, ContentPage

logger = logging.getLogger(__name__)


async def retokenize_user_language_coref(
    ctx: dict,
    user_id_str: str,
    language_id: int,
) -> None:
    """Enqueue tokenize_page for all pages the user owns in this language."""
    redis: Redis = ctx["redis"]
    user_id = uuid.UUID(user_id_str)

    async with AsyncSessionFactory() as session:
        items_result = await session.execute(
            sa.select(ContentItem.id).where(
                ContentItem.user_id == user_id,
                ContentItem.language_id == language_id,
                ContentItem.status == "completed",
            )
        )
        item_ids = [row.id for row in items_result]

    if not item_ids:
        logger.info(
            "retokenize_user_language_coref: no completed items for user=%s lang=%d",
            user_id,
            language_id,
        )
        return

    total_enqueued = 0
    async with AsyncSessionFactory() as session:
        for item_id in item_ids:
            pages_result = await session.execute(
                sa.select(ContentPage.id).where(
                    ContentPage.content_item_id == item_id,
                    ContentPage.status == "ready",
                )
            )
            page_ids = [str(row.id) for row in pages_result]
            for pid in page_ids:
                await redis.enqueue_job("tokenize_page", pid)  # type: ignore[attr-defined]
                total_enqueued += 1

    logger.info(
        "retokenize_user_language_coref: enqueued %d pages for user=%s lang=%d",
        total_enqueued,
        user_id,
        language_id,
    )
