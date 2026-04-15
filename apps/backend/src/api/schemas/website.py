"""Pydantic schemas for website import API."""
from typing import Optional

from pydantic import BaseModel


class WebsitePreviewRequest(BaseModel):
    url: str


class WebsitePreviewResponse(BaseModel):
    url: str
    title: str
    excerpt: str
    word_count: int
    author: Optional[str] = None


class WebsiteImportRequest(BaseModel):
    url: str
    title: str
    language_id: int


class WebsiteImportResponse(BaseModel):
    id: str
    title: str
    status: str
    language_id: int
