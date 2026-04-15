import asyncio
import logging
import uuid

import sqlalchemy as sa
from redis.asyncio import Redis

from src.infrastructure.db.engine import AsyncSessionFactory
from src.infrastructure.db.models.content import Book, ContentItem, ContentPage
from src.infrastructure.db.models.languages import LanguageNlpConfig
from src.infrastructure.db.models.providers import Provider
from src.infrastructure.db.models.users import User, UserLanguageProfile
from src.infrastructure.db.repositories.word_repo import WordRepository
from src.infrastructure.stanza.client import StanzaClient
from src.worker.events import publish_import_event

logger = logging.getLogger(__name__)

_word_repo = WordRepository()

_TOTAL_KEY = "book:{book_id}:total_pages"
_COMPLETED_KEY = "book:{book_id}:completed_pages"
_TOKEN_COUNT_KEY = "book:{book_id}:token_count"
_FINALIZING_KEY = "book:{book_id}:finalizing"
_REDIS_TTL = 86400  # 24 h


async def tokenize_page(ctx: dict, page_id: str) -> None:
    page_uuid = uuid.UUID(page_id)
    redis: Redis = ctx["redis"]
    stanza_client: StanzaClient = ctx["stanza_client"]

    async with AsyncSessionFactory() as session:
        page, content_item, stanza_lang = await _load_page_context(session, page_uuid)
        if page is None or content_item is None:
            return

        auto_ignore_propn = await _resolve_auto_ignore(
            session, content_item.user_id, content_item.language_id
        )

        token_dicts: list[dict] = await asyncio.to_thread(
            stanza_client.tokenize_sync, stanza_lang, page.text
        )

        # Build surface → lemma map for read-time enrichment (migration 0042).
        page.lemma_map = {
            t["w"].lower().strip(): (t.get("l") or t["w"]).lower().strip()
            for t in token_dicts
            if t["w"].strip()
        }

        word_rows = _build_word_rows(
            token_dicts, content_item.user_id, content_item.language_id, auto_ignore_propn
        )
        await _word_repo.bulk_upsert(
            session,
            user_id=content_item.user_id,
            language_id=content_item.language_id,
            rows=word_rows,
        )

        page.status = "ready"
        await session.commit()

    book_id = content_item.id
    completed, total = await _update_progress(redis, book_id, len(token_dicts))

    logger.info("Tokenized page %s (%d/%d, book=%s)", page_uuid, completed, total, book_id)
    await publish_import_event(redis, book_id, "progress", {"page": completed, "total": total})

    if total > 0 and completed >= total:
        await _try_finalize(redis, book_id, completed)


async def _load_page_context(
    session, page_uuid: uuid.UUID
) -> tuple[ContentPage | None, ContentItem | None, str]:
    """Load the page, its parent content item, and NLP language name.

    Returns (None, None, "") if any required record is missing or unsupported.
    """
    page = await session.get(ContentPage, page_uuid)
    if page is None:
        logger.error("ContentPage %s not found", page_uuid)
        return None, None, ""

    content_item = await session.get(ContentItem, page.content_item_id)
    if content_item is None:
        logger.error("ContentItem %s not found for page %s", page.content_item_id, page_uuid)
        return None, None, ""

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
    return page, content_item, stanza_lang


async def _resolve_auto_ignore(session, user_id: uuid.UUID, language_id: int) -> bool:
    """Return the effective auto_ignore_proper_nouns setting for this user/language."""
    user = await session.get(User, user_id)
    global_setting = getattr(user, "auto_ignore_proper_nouns", True) if user else True

    lang_profile = await session.scalar(
        sa.select(UserLanguageProfile).where(
            UserLanguageProfile.user_id == user_id,
            UserLanguageProfile.language_id == language_id,
        )
    )
    if lang_profile and lang_profile.auto_ignore_proper_nouns is not None:
        return lang_profile.auto_ignore_proper_nouns
    return global_setting


def _build_word_rows(
    token_dicts: list[dict],
    user_id: uuid.UUID,
    language_id: int,
    auto_ignore_propn: bool,
) -> list[dict]:
    """Deduplicate tokens and build word rows for bulk upsert."""
    seen: set[str] = set()
    rows: list[dict] = []
    for t in token_dicts:
        # Key by lemma; fall back to surface form if Stanza produced no lemma.
        lemma = (t.get("l") or t["w"]).lower().strip()
        if not lemma or lemma in seen:
            continue
        seen.add(lemma)
        is_propn = auto_ignore_propn and t.get("pos") == "PROPN"
        rows.append({
            "user_id": user_id,
            "language_id": language_id,
            "word": lemma,
            "lemma": lemma,
            "pos": t.get("pos", ""),
            "reading": t.get("r", ""),
            "gender": t.get("g", ""),
            "feats": t.get("feats", ""),
            "dep_head": t.get("dep_head", 0),
            "dep_rel": t.get("dep_rel", ""),
            "status": "ignored" if is_propn else "new",
        })
    return rows


async def _update_progress(redis: Redis, book_id: uuid.UUID, token_count: int) -> tuple[int, int]:
    """Increment Redis counters and return (completed, total)."""
    completed_key = _COMPLETED_KEY.format(book_id=book_id)
    total_key = _TOTAL_KEY.format(book_id=book_id)
    token_count_key = _TOKEN_COUNT_KEY.format(book_id=book_id)

    completed = await redis.incr(completed_key)
    await redis.incrby(token_count_key, token_count)
    await redis.expire(token_count_key, _REDIS_TTL)

    total_raw = await redis.get(total_key)
    total = int(total_raw) if total_raw else 0
    return int(completed), total


async def _try_finalize(redis: Redis, book_id: uuid.UUID, completed: int) -> None:
    """Claim finalization via SETNX and run _finalize exactly once per book."""
    finalizing_key = _FINALIZING_KEY.format(book_id=book_id)
    acquired = await redis.setnx(finalizing_key, "1")
    if not acquired:
        return

    await redis.expire(finalizing_key, _REDIS_TTL)
    try:
        await _finalize(redis, book_id, completed)
    finally:
        await redis.delete(_COMPLETED_KEY.format(book_id=book_id))
        await redis.delete(_TOTAL_KEY.format(book_id=book_id))
        await redis.delete(_TOKEN_COUNT_KEY.format(book_id=book_id))
        await redis.delete(finalizing_key)


async def _finalize(redis: Redis, book_id: uuid.UUID, page_count: int) -> None:
    logger.info("Finalizing book: book_id=%s", book_id)

    token_count_raw = await redis.get(_TOKEN_COUNT_KEY.format(book_id=book_id))
    total_token_count = int(token_count_raw) if token_count_raw else 0

    has_audio_overlay = False
    async with AsyncSessionFactory() as session:
        content_item = await session.get(ContentItem, book_id)
        if content_item is None:
            logger.error("ContentItem %s not found during finalization", book_id)
            return

        book = await session.get(Book, book_id)
        if book:
            has_audio_overlay = bool(book.has_audio_overlay)

        content_item.status = "completed"
        content_item.word_count = total_token_count
        await session.commit()

    await publish_import_event(
        redis,
        book_id,
        "completed",
        {"word_count": total_token_count, "page_count": page_count},
    )
    logger.info(
        "Book import complete: book_id=%s pages=%d tokens=%d",
        book_id,
        page_count,
        total_token_count,
    )

    if has_audio_overlay:
        await redis.enqueue_job("align_smil_audio", str(book_id))  # type: ignore[attr-defined]
        logger.info("Enqueued align_smil_audio for book %s", book_id)
