"""YouTube import API routes."""
from arq import ArqRedis
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_arq_pool, get_current_user, get_db
from src.core.config import get_settings
from src.api.schemas.youtube import (
    YouTubeImportRequest,
    YouTubeImportResponse,
    YouTubePreviewResponse,
    YouTubeStatusResponse,
    YouTubeSubtitleUploadResponse,
)
from src.infrastructure.db.models.content import ContentItem
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.content_repo import ContentRepository
from src.infrastructure.db.repositories.youtube_repo import YouTubeRepository
from src.infrastructure.youtube.fetcher import YouTubeMetadataFetcher
from src.infrastructure.youtube.srt_parser import parse_srt

router = APIRouter(prefix="/youtube", tags=["youtube"])
_content_repo = ContentRepository()
_youtube_repo = YouTubeRepository()
_fetcher = YouTubeMetadataFetcher()


@router.get("/preview", response_model=YouTubePreviewResponse)
async def preview_youtube_video(
    url: str = Query(..., description="YouTube video URL"),
) -> YouTubePreviewResponse:
    """Fetch metadata and available subtitle tracks for a YouTube video.

    No database writes. Returns metadata for preview before import.

    Args:
        url: YouTube video URL

    Returns:
        YouTubePreviewResponse with video details and subtitle availability
    """
    try:
        metadata = _fetcher.fetch_metadata(url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch video: {str(e)}",
        ) from e

    return YouTubePreviewResponse(
        video_id=metadata["video_id"],
        title=metadata["title"],
        duration_ms=metadata["duration_ms"],
        channel_name=metadata["channel_name"],
        thumbnail_url=metadata["thumbnail_url"],
        available_subtitles=metadata["available_subtitles"],
    )


@router.post("/import", response_model=YouTubeImportResponse, status_code=202)
async def import_youtube_video(
    request: YouTubeImportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> YouTubeImportResponse:
    """Import a YouTube video and its subtitles.

    Creates a ContentItem + YouTubeVideo record, fetches and stores subtitles,
    and enqueues an async task for further processing.

    Args:
        request: YouTube import request with URL, title, language, subtitle preferences
        current_user: Authenticated user
        session: Database session
        arq_pool: ARQ job queue pool

    Returns:
        YouTubeImportResponse with video_id, content_item_id, and status
    """
    # Fetch metadata to validate URL and get video ID
    try:
        metadata = _fetcher.fetch_metadata(request.url)
        video_id = metadata["video_id"]
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid YouTube URL: {str(e)}",
        ) from e

    # Create ContentItem
    content_item = await _content_repo.create_content_item(
        session=session,
        user_id=current_user.id,
        language_id=request.language_id,
        type="youtube",
        title=request.title,
    )

    # Create YouTubeVideo record
    subtitle_source = "auto-generated" if request.use_auto_captions else "user-uploaded"
    await _youtube_repo.create_video(
        session=session,
        id=content_item.id,
        video_id=video_id,
        youtube_url=request.url,
        channel_name=metadata.get("channel_name"),
        video_duration_ms=metadata.get("duration_ms"),
        subtitle_lang_code=request.subtitle_lang_code,
        subtitle_source=subtitle_source,
    )

    # Fetch subtitles from YouTube
    try:
        subtitles = _fetcher.fetch_subtitles(
            url=request.url,
            lang_code=request.subtitle_lang_code,
            use_auto=request.use_auto_captions,
        )
    except Exception as e:
        # Mark import as failed, but don't fail the request
        await _content_repo.update_status(
            session=session,
            content_item_id=content_item.id,
            status="failed",
            error_message=f"Failed to fetch subtitles: {str(e)}",
        )
        await session.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch subtitles: {str(e)}",
        ) from e

    # Store subtitles in database
    if subtitles:
        await _youtube_repo.create_subtitles_batch(
            session=session,
            video_id=video_id,
            subtitles=subtitles,
        )

    await session.commit()

    # Enqueue background task: (video_id, content_item_id, language_id)
    await arq_pool.enqueue_job(
        "import_youtube_subtitles",
        video_id,
        str(content_item.id),
        request.language_id,
    )

    return YouTubeImportResponse(
        video_id=video_id,
        content_item_id=str(content_item.id),
        status="in_progress",
    )


@router.get("/{video_id}/status", response_model=YouTubeStatusResponse)
async def get_youtube_status(
    video_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> YouTubeStatusResponse:
    """Poll import status for a YouTube video."""
    video = await _youtube_repo.find_by_video_id(session, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    content_item = await session.get(ContentItem, video.id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Video not found")

    return YouTubeStatusResponse(
        video_id=video_id,
        content_item_id=str(content_item.id),
        status=content_item.status,
        error_message=content_item.error_message,
    )


@router.post(
    "/{video_id}/subtitles/upload",
    response_model=YouTubeSubtitleUploadResponse,
)
async def upload_youtube_subtitles(
    video_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> YouTubeSubtitleUploadResponse:
    """Upload and replace subtitles for a YouTube video via .srt file.

    Parses .srt file and replaces existing subtitles for the given video_id.

    Args:
        video_id: YouTube video ID
        file: .srt file upload
        current_user: Authenticated user
        session: Database session

    Returns:
        YouTubeSubtitleUploadResponse with video_id, status, and line count
    """
    # Check that video exists and belongs to current user
    video = await _youtube_repo.find_by_video_id(session, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Verify user owns this video (check via content_item)
    content_item = await session.get(ContentItem, video.id)
    if not content_item or content_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this video")

    # Read .srt file with a size cap so a huge upload can't OOM the server.
    max_bytes = get_settings().max_upload_bytes
    raw = await file.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Subtitle file too large. Max {max_bytes // (1024 * 1024)} MB.",
        )
    try:
        srt_content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be valid UTF-8 text",
        ) from None

    # Parse SRT
    subtitles = parse_srt(srt_content)
    if not subtitles:
        raise HTTPException(
            status_code=400,
            detail="No valid subtitle lines found in .srt file",
        )

    # Delete existing subtitles and replace with new ones
    await _youtube_repo.delete_subtitles_for_video(session, video_id)
    await _youtube_repo.create_subtitles_batch(session, video_id, subtitles)

    await session.commit()

    return YouTubeSubtitleUploadResponse(
        video_id=video_id,
        status="in_progress",
        lines_parsed=len(subtitles),
    )
