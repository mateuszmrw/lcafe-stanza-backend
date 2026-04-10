from src.domain.nlp.models.token import Token
from src.domain.ports.nlp_port import NlpPort


class SpacyNlpAdapter(NlpPort):
    """SpaCy NLP adapter — stub, not yet implemented."""

    def tokenize(self, text: str | list[str], language: str) -> list[Token]:
        raise NotImplementedError("SpaCy adapter is not yet implemented")
