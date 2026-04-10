from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.domain.ports.dictionary_port import DictionaryEntry, FrequencyInfo
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.dictionary_entry_repo import DictionaryEntryRepository
from src.infrastructure.db.repositories.word_frequency_repo import WordFrequencyRepository
from src.infrastructure.db.repositories.provider_repo import ProviderRepository
from src.infrastructure.wiktionary.db_adapter import WiktionaryDbAdapter

router = APIRouter(prefix="/dictionary", tags=["dictionary"])
_provider_repo = ProviderRepository()
_entry_repo = DictionaryEntryRepository()
_freq_repo = WordFrequencyRepository()

_DB_ADAPTERS: dict[str, type] = {
    "wiktionary": WiktionaryDbAdapter,
}

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


class DictionaryProviderResult(BaseModel):
    provider_slug: str
    entries: list[DictionaryEntry]


class DictionaryLookupResponse(BaseModel):
    results: list[DictionaryProviderResult]


@router.get("", response_model=DictionaryLookupResponse)
async def lookup_word(
    word: str,
    source_lang: str,
    target_lang: str,
    provider_slug: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DictionaryLookupResponse:
    providers = await _provider_repo.list_active_by_type(session, "dictionary")
    if provider_slug:
        providers = [p for p in providers if p.slug == provider_slug]

    results: list[DictionaryProviderResult] = []
    for provider in providers:
        adapter_cls = _DB_ADAPTERS.get(provider.slug)
        if adapter_cls is None:
            continue
        has = await _entry_repo.has_entries(session, source_lang, target_lang)
        if not has:
            continue
        adapter = adapter_cls(session)
        entries = await adapter.lookup(word, source_lang, target_lang)

        # Enrich entries with frequency data (all entries share the same lemma/lang)
        freq_row = None
        if entries:
            freq_row = await _freq_repo.lookup(session, source_lang, entries[0].lemma)
        freq_info = (
            FrequencyInfo(rank=freq_row.rank, tier=_rank_to_tier(freq_row.rank))
            if freq_row
            else None
        )
        enriched = [e.model_copy(update={"frequency": freq_info}) for e in entries]

        results.append(DictionaryProviderResult(provider_slug=provider.slug, entries=enriched))

    return DictionaryLookupResponse(results=results)
