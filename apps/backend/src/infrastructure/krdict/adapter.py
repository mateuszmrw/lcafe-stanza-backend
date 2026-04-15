from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.dictionary_port import DictionaryEntry, DictionaryPort
from src.infrastructure.krdict.repository import KrdictRepository

_repo = KrdictRepository()


class KrdictAdapter(DictionaryPort):
    """DictionaryPort backed by the krdict_entries table."""

    source_dict = "krdict"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lookup(
        self, word: str, source_lang: str, target_lang: str
    ) -> list[DictionaryEntry]:
        if source_lang != "ko":
            return []

        rows = await _repo.lookup(self._session, word)
        entries: list[DictionaryEntry] = []

        for row in rows:
            # Collect English translations as the primary glosses list;
            # fall back to Korean definitions when no English is available.
            glosses: list[str] = []
            for defn in row.definitions:
                en = defn.get("en") or defn.get("en_def")
                glosses.append(en if en else defn.get("text", ""))

            entries.append(
                DictionaryEntry(
                    lemma=row.word,
                    pos=row.pos or "",
                    glosses=glosses,
                    forms=[],
                    etymology=None,
                    labels=[],
                    metadata={
                        "hanja": row.hanja,
                        "level": row.level,
                        "definitions": row.definitions,
                    },
                )
            )

        return entries
