import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WordResponse(BaseModel):
    id: uuid.UUID
    word: str
    lemma: str
    pos: str
    reading: str
    gender: str
    status: str
    hint: Optional[str]
    sentence_context: Optional[str] = None
    language_id: int
    lookup_count: int
    exposure_count: int = 0
    difficulty_score: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WordListResponse(BaseModel):
    items: list[WordResponse]
    total: int
    page: int
    limit: int


class VocabularyStatusUpdate(BaseModel):
    status: str


class VocabularyUpsertRequest(BaseModel):
    word: str
    status: str
    language_id: int
    lemma: str = ""
    pos: str = ""
    reading: str = ""
    gender: str = ""
    feats: str = ""
    hint: Optional[str] = None
    sentence_context: Optional[str] = None


class BulkStatusUpdate(BaseModel):
    ids: list[uuid.UUID]
    status: str
