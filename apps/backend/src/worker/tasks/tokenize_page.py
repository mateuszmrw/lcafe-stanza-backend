import asyncio
import logging
import uuid

import sqlalchemy as sa
from redis.asyncio import Redis

from src.infrastructure.db.engine import AsyncSessionFactory
from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.languages import LanguageNlpConfig
from src.infrastructure.db.models.providers import Provider
from src.infrastructure.db.repositories.word_repo import WordRepository
from src.infrastructure.stanza.client import StanzaClient
from src.worker.events import publish_import_event

logger = logging.getLogger(__name__)

_word_repo = WordRepository()

_TOTAL_KEY = "book:{cid}:total_pages"
_COMPLETED_KEY = "book:{cid}:completed_pages"
_TOKEN_COUNT_KEY = "book:{cid}:token_count"
_FINALIZING_KEY = "book:{cid}:finalizing"
_REDIS_TTL = 86400  # 24 h


async def tokenize_page(ctx: dict, page_id: str) -> None:
    page_uuid = uuid.UUID(page_id)
    redis: Redis = ctx["redis"]
    stanza_client: StanzaClient = ctx["stanza_client"]

    async with AsyncSessionFactory() as session:
        page = await session.get(ContentPage, page_uuid)
        if page is None:
            logger.error("ContentPage %s not found", page_uuid)
            return

        content_item_id = page.content_item_id

        content_item = await session.get(ContentItem, content_item_id)
        if content_item is None:
            logger.error("ContentItem %s not found for page %s", content_item_id, page_uuid)
            return

        nlp_config = await session.scalar(
            sa.select(LanguageNlpConfig).where(
                LanguageNlpConfig.language_id == content_item.language_id
            )
        )
        if nlp_config is None:
            raise RuntimeError(f"No NLP config for language_id={content_item.language_id}")

        provider = await session.get(Provider, nlp_config.provider_id)
        if provider is None or provider.slug != "stanza":
            raise NotImplementedError(
                f"Provider '{getattr(provider, 'slug', None)}' not supported"
            )

        stanza_lang: str = nlp_config.config.get("stanza_language_name", "english")

        # Tokenize in a background thread — Stanza is CPU-bound and not async-friendly.
        token_dicts: list[dict] = await asyncio.to_thread(
            stanza_client.tokenize_sync, stanza_lang, page.text
        )

        # Upsert this page's unique words into the vocabulary table immediately.
        # Words are user/language-scoped and independent of books — each page
        # contributes its new words as soon as it's tokenized.
        seen: set[str] = set()
        word_rows: list[dict] = []
        for t in token_dicts:
            key = t["w"].lower().strip()
            if key and key not in seen:
                seen.add(key)
                word_rows.append(
                    {
                        "user_id": content_item.user_id,
                        "language_id": content_item.language_id,
                        "word": key,
                        "lemma": t.get("l", ""),
                        "pos": t.get("pos", ""),
                        "reading": t.get("r", ""),
                        "gender": t.get("g", ""),
                        "feats": t.get("feats", ""),
                        "dep_head": t.get("dep_head", 0),
                        "dep_rel": t.get("dep_rel", ""),
                    }
                )

        await _word_repo.bulk_upsert(
            session,
            user_id=content_item.user_id,
            language_id=content_item.language_id,
            rows=word_rows,
        )

        page.status = "ready"
        await session.commit()

    # Progress tracking
    total_key = _TOTAL_KEY.format(cid=content_item_id)
    completed_key = _COMPLETED_KEY.format(cid=content_item_id)
    token_count_key = _TOKEN_COUNT_KEY.format(cid=content_item_id)
    finalizing_key = _FINALIZING_KEY.format(cid=content_item_id)

    completed = await redis.incr(completed_key)
    await redis.incrby(token_count_key, len(token_dicts))
    await redis.expire(token_count_key, _REDIS_TTL)

    total_raw = await redis.get(total_key)
    total = int(total_raw) if total_raw else 0

    logger.info("Tokenized page %s (%d/%d, book=%s)", page_uuid, completed, total, content_item_id)

    await publish_import_event(
        redis, content_item_id, "progress", {"page": int(completed), "total": total}
    )

    if total > 0 and completed >= total:
        # Claim finalization via SETNX — only one worker runs this even if two
        # jobs race to complete the last page simultaneously.
        acquired = await redis.setnx(finalizing_key, "1")
        if acquired:
            await redis.expire(finalizing_key, _REDIS_TTL)
            try:
                await _finalize(redis, content_item_id, int(completed))
            finally:
                await redis.delete(completed_key)
                await redis.delete(total_key)
                await redis.delete(token_count_key)
                await redis.delete(finalizing_key)


async def _finalize(redis: Redis, content_item_id: uuid.UUID, page_count: int) -> None:
    logger.info("Finalizing book: content_item_id=%s", content_item_id)

    token_count_raw = await redis.get(_TOKEN_COUNT_KEY.format(cid=content_item_id))
    total_token_count = int(token_count_raw) if token_count_raw else 0

    async with AsyncSessionFactory() as session:
        content_item = await session.get(ContentItem, content_item_id)
        if content_item is None:
            logger.error("ContentItem %s not found during finalization", content_item_id)
            return

        content_item.status = "completed"
        content_item.word_count = total_token_count
        await session.commit()

    await publish_import_event(
        redis,
        content_item_id,
        "completed",
        {"word_count": total_token_count, "page_count": page_count},
    )
    logger.info(
        "Book import complete: content_item_id=%s pages=%d tokens=%d",
        content_item_id,
        page_count,
        total_token_count,
    )
