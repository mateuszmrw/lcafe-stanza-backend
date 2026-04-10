from abc import ABC, abstractmethod


class TranslationPort(ABC):
    @abstractmethod
    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> list[str]: ...
