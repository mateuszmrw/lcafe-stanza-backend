"""Admin endpoints for YouTube video management."""
import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.domain.youtube.chunker import YouTubeSubtitleChunker
from src.infrastructure.db.models.content import ContentPage
from src.infrastructure.db.models.users import User
from src.infrastructure.db.models.youtube import YouTubeSubtitle, YouTubeVideo
from src.infrastructure.db.repositories.audio_repo import AudioRepository

router = APIRouter(prefix="/admin/youtube", tags=["admin"])

_chunker = YouTubeSubtitleChunker()
_audio_repo = AudioRepository()


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
    video = await session.scalar(
        sa.select(YouTubeVideo).where(YouTubeVideo.video_id == video_id)
    )
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    content_item_id: uuid.UUID = video.id

    # Load subtitle lines ordered by line_number
    subtitle_rows = await session.execute(
        sa.select(YouTubeSubtitle)
        .where(YouTubeSubtitle.video_id == video_id)
        .order_by(YouTubeSubtitle.line_number)
    )
    subtitles = list(subtitle_rows.scalars().all())

    if not subtitles:
        raise HTTPException(status_code=400, detail="No subtitles found for this video")

    subtitle_dicts = [
        {"line_number": s.line_number, "start_ms": s.start_ms, "end_ms": s.end_ms, "text": s.text}
        for s in subtitles
    ]

    # Load pages ordered by page_number
    pages_result = await session.execute(
        sa.select(ContentPage)
        .where(ContentPage.content_item_id == content_item_id)
        .order_by(ContentPage.page_number)
    )
    pages = list(pages_result.scalars().all())

    if not pages:
        raise HTTPException(status_code=400, detail="No pages found — run import first")

    # Clear existing alignments
    await _audio_repo.delete_alignments_for_book(session, content_item_id)

    # Re-chunk and re-populate (same logic as import task)
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
