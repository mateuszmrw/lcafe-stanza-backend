from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.domain.ports.dictionary_port import DictionaryEntry, DictionaryPort, FrequencyInfo
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.dictionary_sources_repo import DictionarySourcesRepository
from src.infrastructure.db.repositories.word_frequency_repo import WordFrequencyRepository
from src.infrastructure.cc_cedict.adapter import CcCedictAdapter
from src.infrastructure.dict_cc.adapter import DictCcAdapter
from src.infrastructure.krdict.adapter import KrdictAdapter
from src.infrastructure.openrussian.adapter import OpenRussianAdapter
from src.infrastructure.wiktionary.db_adapter import WiktionaryAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dictionary", tags=["dictionary"])
_sources_repo = DictionarySourcesRepository()
_freq_repo = WordFrequencyRepository()

# Registry: source slug → adapter class.
# Future phases add their adapter classes here.
_ADAPTER_REGISTRY: dict[str, type[DictionaryPort]] = {
    "wiktionary": WiktionaryAdapter,
    "openrussian": OpenRussianAdapter,
    "cc-cedict": CcCedictAdapter,
    "dict.cc": DictCcAdapter,
    "krdict": KrdictAdapter,
}

_CACHE_TTL = 300  # 5 minutes
_ADAPTER_TIMEOUT = 2.0  # seconds per adapter

_TIER_THRESHOLDS = [
    (1_000, "very_common"),
    (5_000, "common"),
    (20_000, "uncommon"),
    (65_000, "rare"),
]


def _rank_to_tier(rank: int) -> str:
    for threshold, tier in _TIER_THRESHOLDS:
        if rank <= threshold:
            return tier
    return "very_rare"


class DictionaryResultGroup(BaseModel):
    source_dict: str
    entries: list[DictionaryEntry]


class DictionaryLookupResponse(BaseModel):
    results: list[DictionaryResultGroup]


@router.get("", response_model=DictionaryLookupResponse)
async def lookup_word(
    word: str,
    source_lang: str,
    target_lang: str,
    dicts: str | None = None,  # comma-separated slugs filter, e.g. "wiktionary,openrussian"
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> DictionaryLookupResponse:
    word_norm = word.lower().strip()
    slug_filter = {s.strip() for s in dicts.split(",")} if dicts else None
    cache_key = f"dict:{source_lang}:{target_lang}:{word_norm}:{dicts or 'all'}"

    # --- cache hit ---
    cached = await redis.get(cache_key)
    if cached:
        try:
            return DictionaryLookupResponse.model_validate_json(cached)
        except Exception:
            pass  # stale / corrupt — fall through to DB

    # --- load active sources ---
    active_sources = await _sources_repo.list_active(session)
    if slug_filter:
        active_sources = [s for s in active_sources if s.slug in slug_filter]

    # --- parallel adapter lookup with per-adapter timeout ---
    async def _call_adapter(slug: str) -> tuple[str, list[DictionaryEntry]]:
        adapter_cls = _ADAPTER_REGISTRY.get(slug)
        if adapter_cls is None:
            return slug, []
        adapter = adapter_cls(session)
        try:
            entries = await asyncio.wait_for(
                adapter.lookup(word_norm, source_lang, target_lang),
                timeout=_ADAPTER_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("Dictionary adapter '%s' timed out for word '%s'", slug, word_norm)
            entries = []
        except Exception as exc:
            logger.warning("Dictionary adapter '%s' error: %s", slug, exc)
            entries = []
        return slug, entries

    tasks = [_call_adapter(source.slug) for source in active_sources]
    adapter_results: list[tuple[str, list[DictionaryEntry]]] = await asyncio.gather(*tasks)

    # --- enrich with frequency info (lemma from first result) ---
    first_lemma: str | None = None
    for _, entries in adapter_results:
        if entries:
            first_lemma = entries[0].lemma
            break

    freq_info: FrequencyInfo | None = None
    if first_lemma:
        freq_row = await _freq_repo.lookup(session, source_lang, first_lemma)
        if freq_row is None and first_lemma != word_norm:
            freq_row = await _freq_repo.lookup(session, source_lang, word_norm)
        if freq_row:
            freq_info = FrequencyInfo(rank=freq_row.rank, tier=_rank_to_tier(freq_row.rank))

    # --- build response ---
    results: list[DictionaryResultGroup] = []
    for slug, entries in adapter_results:
        if not entries:
            continue
        if freq_info:
            entries = [e.model_copy(update={"frequency": freq_info}) for e in entries]
        results.append(DictionaryResultGroup(source_dict=slug, entries=entries))

    response = DictionaryLookupResponse(results=results)

    # --- cache result ---
    try:
        await redis.set(cache_key, response.model_dump_json(), ex=_CACHE_TTL)
    except Exception as exc:
        logger.warning("Failed to cache dictionary result: %s", exc)

    return response
