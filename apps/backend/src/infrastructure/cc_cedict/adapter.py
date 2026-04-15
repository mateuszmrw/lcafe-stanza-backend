from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.dictionary_port import DictionaryEntry, DictionaryPort
from src.infrastructure.cc_cedict.repository import CcCedictRepository

_repo = CcCedictRepository()


class CcCedictAdapter(DictionaryPort):
    """DictionaryPort backed by the cc_cedict_entries table."""

    source_dict = "cc-cedict"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lookup(
        self, word: str, source_lang: str, target_lang: str
    ) -> list[DictionaryEntry]:
        if source_lang != "zh":
            return []

        rows = await _repo.lookup(self._session, word)
        entries: list[DictionaryEntry] = []

        for row in rows:
            entries.append(
                DictionaryEntry(
                    lemma=row.simplified,
                    pos="",  # CC-CEDICT doesn't have a reliable top-level POS
                    glosses=row.glosses,
                    forms=(
                        [{"form": row.traditional, "tags": ["traditional"]}]
                        if row.traditional != row.simplified
                        else []
                    ),
                    etymology=None,
                    labels=[],
                    metadata={
                        "traditional": row.traditional,
                        "pinyin": row.pinyin,
                    },
                )
            )

        return entries
