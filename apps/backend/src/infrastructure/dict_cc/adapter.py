from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.dictionary_port import DictionaryEntry, DictionaryPort
from src.infrastructure.dict_cc.repository import DictCcRepository

_repo = DictCcRepository()


class DictCcAdapter(DictionaryPort):
    """DictionaryPort backed by the dict_cc_entries table."""

    source_dict = "dict.cc"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lookup(
        self, word: str, source_lang: str, target_lang: str
    ) -> list[DictionaryEntry]:
        rows = await _repo.lookup(self._session, word, source_lang, target_lang)
        entries: list[DictionaryEntry] = []

        for row in rows:
            entries.append(
                DictionaryEntry(
                    lemma=row.source_word,
                    pos=row.pos or "",
                    glosses=[row.target_word],
                    forms=[],
                    etymology=None,
                    labels=[],
                    metadata={
                        "target_word": row.target_word,
                        "notes": row.notes,
                    },
                )
            )

        return entries
