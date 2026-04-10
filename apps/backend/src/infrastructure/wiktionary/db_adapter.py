from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.dictionary_port import DictionaryEntry, DictionaryPort
from src.infrastructure.db.repositories.dictionary_entry_repo import DictionaryEntryRepository

_repo = DictionaryEntryRepository()


class WiktionaryDbAdapter(DictionaryPort):
    """DictionaryPort backed by the local dictionary_entries table (bilingual)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lookup(
        self, word: str, source_lang: str, target_lang: str
    ) -> list[DictionaryEntry]:
        rows = await _repo.lookup(self._session, word.lower(), source_lang, target_lang)
        return [
            DictionaryEntry(
                lemma=row.word,
                pos=row.pos,
                glosses=row.glosses,
                forms=row.forms,
                etymology=row.etymology,
                labels=row.labels,
            )
            for row in rows
        ]
