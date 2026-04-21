from pydantic import BaseModel


class TokenInput(BaseModel):
    w: str
    l: str
    pos: str
    x: str = ""   # language-specific POS tag (xpos)
    feats: str = ""
    dep_head: int = 0   # 1-based head index (0 = root)
    dep_rel: str = ""   # UD relation label, e.g. "nsubj", "obj"


class TokenAnnotation(BaseModel):
    w: str
    annotation: str


class GrammarExplainRequest(BaseModel):
    tokens: list[TokenInput]
    language_code: str
    register: str | None = None


class GrammarExplainResponse(BaseModel):
    token_annotations: list[TokenAnnotation]
    prose_explanation: str
