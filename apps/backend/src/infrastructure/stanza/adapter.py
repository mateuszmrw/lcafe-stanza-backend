from src.domain.nlp.models.token import Token
from src.domain.ports.nlp_port import NlpPort
from src.infrastructure.stanza.client import StanzaClient


class StanzaNlpAdapter(NlpPort):
    """NlpPort implementation backed by Stanza.

    stanza_language_name is the full language name Stanza expects (e.g. "russian"),
    sourced from language_nlp_config.config["stanza_language_name"].
    """

    def __init__(self, client: StanzaClient, stanza_language_name: str) -> None:
        self._client = client
        self._lang = stanza_language_name

    def tokenize(self, text: str | list[str], language: str) -> list[Token]:
        pipeline = self._client.get_pipeline(self._lang)
        texts = [text] if isinstance(text, str) else text
        tokens: list[Token] = []
        for t in texts:
            doc = pipeline(t)
            for i, sentence in enumerate(doc.sentences):
                for word in sentence.words:
                    tokens.append(
                        Token(
                            w=word.text,
                            r="",
                            l=word.lemma or "",
                            lr="",
                            pos=word.upos or "",
                            si=i,
                            g=_extract_gender(word.feats),
                        )
                    )
        return tokens


def _extract_gender(feats: str | None) -> str:
    if not feats:
        return ""
    for feat in feats.split("|"):
        if feat.startswith("Gender="):
            return feat.split("=")[1]
    return ""
