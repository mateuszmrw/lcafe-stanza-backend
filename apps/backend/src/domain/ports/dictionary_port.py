from abc import ABC, abstractmethod

from pydantic import BaseModel


class FrequencyInfo(BaseModel):
    rank: int
    tier: str  # "very_common" | "common" | "uncommon" | "rare"


class DictionaryEntry(BaseModel):
    lemma: str
    pos: str
    glosses: list[str]
    forms: list[dict]  # each dict: {"form": str, "tags": list[str]}
    etymology: str | None = None
    labels: list[str] = []
    frequency: FrequencyInfo | None = None
    # Source-specific extra data (e.g. accented form, aspect, examples for OpenRussian).
    # Never used for lookup — only for richer frontend rendering.
    metadata: dict | None = None


class DictionaryPort(ABC):
    @abstractmethod
    async def lookup(
        self, word: str, source_lang: str, target_lang: str
    ) -> list[DictionaryEntry]: ...
