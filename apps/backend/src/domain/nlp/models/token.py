from pydantic import BaseModel, Field


class Token(BaseModel):
    w: str  ## word
    r: str  ## reading
    l: str  ## lemma
    lr: str  ## lemma reading
    pos: str  ## part of speech
    x: str = ""  ## language-specific POS tag (xpos)
    si: int  ## sentence index
    g: str  ## gender
    e: str = ""  ## entity type (PER/LOC/ORG/...)
    eb: str = ""  ## entity IOB boundary (B/I)
    m: list[str] = Field(default_factory=list)  ## morpheme segments (RU only)

    cc: int = 0
    ch: bool = False
    cr: str = ""
    cz: bool = False
    mwt_group_id: int | None = None

    def to_dict(self):
        return {
            "w": self.w,
            "r": self.r,
            "l": self.l,
            "lr": self.lr,
            "pos": self.pos,
            "x": self.x,
            "si": self.si,
            "g": self.g,
            "e": self.e,
            "eb": self.eb,
            "m": self.m,
            "cc": self.cc,
            "ch": self.ch,
            "cr": self.cr,
            "cz": self.cz,
            "mwt_group_id": self.mwt_group_id,
        }
