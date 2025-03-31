from pydantic import BaseModel


class Token(BaseModel):
    w: str ## word
    r: str ## reading   
    l: str ## lemma
    lr: str ## lemma reading
    pos: str ## part of speech
    si: int ## sentence index
    g: str ## gender

    def to_dict(self):
        return {
            'w': self.w,
            'r': self.r,
            'l': self.l,
            'lr': self.lr,
            'pos': self.pos,
            'si': self.si,
            'g': self.g
        }
