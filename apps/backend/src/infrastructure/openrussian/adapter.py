from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.dictionary_port import DictionaryEntry, DictionaryPort
from src.infrastructure.openrussian.repository import OpenRussianRepository

_repo = OpenRussianRepository()

# Map OpenRussian lowercase POS tags to Universal POS tags used by Stanza
_POS_MAP: dict[str, str] = {
    "noun": "NOUN",
    "verb": "VERB",
    "adj": "ADJ",
    "other": "X",
}


class OpenRussianAdapter(DictionaryPort):
    """DictionaryPort backed by the openrussian_words table."""

    source_dict = "openrussian"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lookup(
        self, word: str, source_lang: str, target_lang: str
    ) -> list[DictionaryEntry]:
        if source_lang != "ru":
            return []

        rows = await _repo.lookup(self._session, word)
        entries: list[DictionaryEntry] = []

        for row in rows:
            pos = _POS_MAP.get(row.pos or "", row.pos.upper() if row.pos else "")

            # glosses: [{text: "..."}] → list[str]
            glosses = [g["text"] for g in (row.glosses or []) if g.get("text")]

            # labels: aspect tag + any info strings from glosses
            labels: list[str] = []
            if row.aspect:
                labels.append(row.aspect)

            # forms are already stored as [{"form": "...", "tags": [...]}]
            forms = [
                {"form": f["form"], "tags": f.get("tags", [])}
                for f in (row.forms or [])
                if f.get("form")
            ]

            # Source-specific metadata for richer frontend rendering
            metadata: dict = {}
            if row.accented:
                metadata["accented"] = row.accented
            if row.aspect:
                metadata["aspect"] = row.aspect

            entries.append(
                DictionaryEntry(
                    lemma=row.bare,
                    pos=pos,
                    glosses=glosses,
                    forms=forms,
                    etymology=None,
                    labels=labels,
                    metadata=metadata if metadata else None,
                )
            )

        return entries
