from src.domain.models.token import Token
from src.infrastructure.external.stanza_client import StanzaClient
import stanza

class Tokenizer():
    def __init__(self, text: str | list[str], language: str, stanza_client: StanzaClient):
        self.text = text
        self.language = language
        self.stanza_client = stanza_client

    def get_stanza_doc(self) -> list[stanza.Document]:
        pipeline = self.stanza_client.get_pipeline(self.language)
        docs = []
        print(self.text)
        if isinstance(self.text, str):
            doc = pipeline(self.text)
            docs.append(doc)
        else:
            for text in self.text:
                doc = pipeline(text)
                docs.append(doc)
        return docs
        

    def tokenize(self) -> list[Token]:
        docs = self.get_stanza_doc()
        tokens: list[Token] = []

        for doc in docs:
            for i, sentence in enumerate(doc.sentences):
                for token in sentence.words:
                    base_token = Token(
                        w=token.text,
                        r="",
                        l=token.lemma,
                        lr="",
                        pos=token.upos,
                        si=i,
                        g=self.extract_gender(token.feats)  
                    )
                    tokens.append(base_token.to_dict())
        return tokens


    def extract_gender(self, feats: str | None) -> str:
        if feats is None:
            return ""
        splitted_feats = feats.split("|")
        for feat in splitted_feats:
            if "Gender=" in feat:
                return feat.split("=")[1]
        return ""