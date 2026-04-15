"""Pydantic schemas for YouTube import API."""
from typing import Optional

from pydantic import BaseModel


class AvailableSubtitle(BaseModel):
    """Available subtitle track for a video."""

    lang_code: str
    label: str
    is_auto: bool


class YouTubePreviewResponse(BaseModel):
    """Response for GET /youtube/preview endpoint."""

    video_id: str
    title: str
    duration_ms: Optional[int]
    channel_name: Optional[str]
    thumbnail_url: Optional[str]
    available_subtitles: list[AvailableSubtitle]


class YouTubeImportRequest(BaseModel):
    """Request body for POST /youtube/import endpoint."""

    url: str
    title: str
    language_id: int
    subtitle_lang_code: str
    use_auto_captions: bool


class YouTubeImportResponse(BaseModel):
    """Response for POST /youtube/import endpoint (202 Accepted)."""

    video_id: str
    content_item_id: str
    status: str


class YouTubeSubtitleUploadResponse(BaseModel):
    """Response for POST /youtube/{video_id}/subtitles/upload endpoint."""

    video_id: str
    status: str
    lines_parsed: int


class YouTubeStatusResponse(BaseModel):
    """Response for GET /youtube/{video_id}/status endpoint."""

    video_id: str
    content_item_id: str
    status: str
    error_message: Optional[str] = None
