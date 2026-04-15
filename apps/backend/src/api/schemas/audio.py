from typing import Optional

from pydantic import BaseModel


class AudioStatusResponse(BaseModel):
    has_audio_overlay: bool
    audio_overlay_status: str
    audio_duration_ms: Optional[int]
    sentences_aligned: int


class SentenceAlignmentResponse(BaseModel):
    sentence_index: int
    audio_start_ms: int
    audio_end_ms: int
    audio_file: Optional[str] = None


class TtsStatusResponse(BaseModel):
    tts_status: str  # none | pending | in_progress | complete | failed
    pages_total: int
    pages_ready: int  # pages with tts_manifest_path set


class TtsGenerateRequest(BaseModel):
    pass  # no params for now — language inferred from book
