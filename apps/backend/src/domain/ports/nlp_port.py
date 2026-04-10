from abc import ABC, abstractmethod

from src.domain.nlp.models.token import Token


class NlpPort(ABC):
    @abstractmethod
    def tokenize(self, text: str | list[str], language: str) -> list[Token]: ...
