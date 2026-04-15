import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TokenWithStatus(BaseModel):
    id: Optional[str] = None  # Word DB UUID, None if word not in vocabulary
    w: str
    l: str
    pos: str
    r: str
    pi: int  # paragraph index within the page
    si: int  # sentence index within the page (global, not per-paragraph)
    g: str
    f: str = ""   # morphological features, e.g. "Gender=Masc|Number=Sing|Case=Nom"
    dep_head: int = 0   # 1-based head token index within sentence (0 = root)
    dep_rel: str = ""   # Universal Dependency relation label, e.g. "nsubj", "obj"
    hint: Optional[str] = None
    status: str = "new"
    d: Optional[int] = None  # difficulty score 0-100


class BookUploadResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    language_id: int


class BookListItem(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    status: str
    word_count: Optional[int]
    language_id: int
    created_at: datetime
    coverage_pct: Optional[int] = None

    model_config = {"from_attributes": True}


class BookListResponse(BaseModel):
    items: list[BookListItem]
    total: int


class BookDetailResponse(BaseModel):
    id: uuid.UUID
    type: str = "book"
    title: str
    description: Optional[str]
    register: Optional[str] = None
    status: str
    word_count: Optional[int]
    page_count: Optional[int]
    language_id: int
    language_code: str
    chapter_count: Optional[int]
    created_at: datetime
    has_audio: bool = False
    audio_duration_ms: Optional[int] = None
    has_audio_overlay: bool = False
    audio_overlay_status: str = "none"
    tts_status: str = "none"
    video_id: Optional[str] = None
    source_url: Optional[str] = None


class PageResponse(BaseModel):
    id: uuid.UUID
    page_number: int
    chapter_number: Optional[int]
    chapter_name: Optional[str]
    chapter_page_number: Optional[int]
    status: str
    text: str
    tokens: list[TokenWithStatus]


class PageListResponse(BaseModel):
    items: list[PageResponse]
    total: int
    page: int
    limit: int


class ChapterSummary(BaseModel):
    chapter_number: int
    chapter_name: Optional[str]
    first_page_number: int
    page_count: int
