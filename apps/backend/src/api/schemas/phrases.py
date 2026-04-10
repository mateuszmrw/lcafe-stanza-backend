import uuid
from datetime import datetime

from pydantic import BaseModel


class PhraseCreate(BaseModel):
    language_id: int | None = None
    text: str
    translation: str | None = None
    context: str | None = None
    book_id: uuid.UUID | None = None
    page: int | None = None


class PhraseUpdate(BaseModel):
    status: str


class PhraseResponse(BaseModel):
    id: uuid.UUID
    language_id: int | None
    text: str
    translation: str | None
    context: str | None
    book_id: uuid.UUID | None
    page: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PhraseListResponse(BaseModel):
    items: list[PhraseResponse]
    total: int
    page: int
    limit: int
