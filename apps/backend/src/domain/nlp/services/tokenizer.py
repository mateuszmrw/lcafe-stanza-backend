from src.domain.nlp.models.token import Token
from src.domain.ports.nlp_port import NlpPort


class Tokenizer:
    def __init__(self, nlp_port: NlpPort):
        self._nlp_port = nlp_port

    def tokenize(self, text: str | list[str], language: str) -> list[Token]:
        return self._nlp_port.tokenize(text, language)
