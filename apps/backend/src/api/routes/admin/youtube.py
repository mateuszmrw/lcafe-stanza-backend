"""Admin endpoints for YouTube video management."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.domain.youtube.chunker import YouTubeSubtitleChunker
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.audio_repo import AudioRepository
from src.infrastructure.db.repositories.content_page_repo import ContentPageRepository
from src.infrastructure.db.repositories.youtube_repo import YouTubeRepository

router = APIRouter(prefix="/admin/youtube", tags=["admin"])

_chunker = YouTubeSubtitleChunker()
_audio_repo = AudioRepository()
_yt_repo = YouTubeRepository()
_page_repo = ContentPageRepository()


class RealignResponse(BaseModel):
    video_id: str
    pages_aligned: int
    alignments_created: int


@router.post("/{video_id}/realign", response_model=RealignResponse)
async def realign_youtube_video(
    video_id: str,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> RealignResponse:
    """Re-create sentence_alignments for a YouTube video without re-fetching subtitles.

    Useful when alignments are missing or corrupted after import.
    """
    video = await _yt_repo.find_by_video_id(session, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    content_item_id: uuid.UUID = video.id

    subtitles = await _yt_repo.get_subtitles_for_video(session, video_id)
    if not subtitles:
        raise HTTPException(status_code=400, detail="No subtitles found for this video")

    subtitle_dicts = [
        {"line_number": s.line_number, "start_ms": s.start_ms, "end_ms": s.end_ms, "text": s.text}
        for s in subtitles
    ]

    pages = await _page_repo.list_by_book(session, content_item_id)
    if not pages:
        raise HTTPException(status_code=400, detail="No pages found — run import first")

    await _audio_repo.delete_alignments_for_book(session, content_item_id)

    chunks = _chunker.chunk(subtitle_dicts, lines_per_page=20)
    total_alignments = 0

    for page, chunk in zip(pages, chunks):
        alignments = [
            {
                "sentence_index": j,
                "audio_start_ms": line["start_ms"],
                "audio_end_ms": line["end_ms"],
            }
            for j, line in enumerate(chunk)
        ]
        await _audio_repo.upsert_alignments(session, page.id, alignments)
        total_alignments += len(alignments)

    await session.commit()

    return RealignResponse(
        video_id=video_id,
        pages_aligned=min(len(pages), len(chunks)),
        alignments_created=total_alignments,
    )
