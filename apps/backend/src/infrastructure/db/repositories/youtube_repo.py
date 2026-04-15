"""YouTube video and subtitle data access layer."""
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.youtube import YouTubeSubtitle, YouTubeVideo


class YouTubeRepository:
    """Repository for YouTube-related database operations."""

    async def create_video(
        self,
        session: AsyncSession,
        id: uuid.UUID,
        video_id: str,
        youtube_url: str,
        channel_name: str | None = None,
        video_duration_ms: int | None = None,
        subtitle_lang_code: str | None = None,
        subtitle_source: str | None = None,
    ) -> YouTubeVideo:
        """Create a new YouTube video record.

        Args:
            session: Database session
            id: Content item ID (FK to content_items)
            video_id: YouTube video ID (11 chars)
            youtube_url: Full YouTube URL
            channel_name: Channel name
            video_duration_ms: Video duration in milliseconds
            subtitle_lang_code: Language code of imported subtitles
            subtitle_source: "auto-generated" or "user-uploaded"

        Returns:
            Created YouTubeVideo instance
        """
        video = YouTubeVideo(
            id=id,
            video_id=video_id,
            youtube_url=youtube_url,
            channel_name=channel_name,
            video_duration_ms=video_duration_ms,
            subtitle_lang_code=subtitle_lang_code,
            subtitle_source=subtitle_source,
        )
        session.add(video)
        await session.flush()
        return video

    async def find_by_video_id(
        self, session: AsyncSession, video_id: str
    ) -> YouTubeVideo | None:
        """Find video by YouTube video ID.

        Args:
            session: Database session
            video_id: YouTube video ID

        Returns:
            YouTubeVideo instance or None if not found
        """
        result = await session.execute(
            sa.select(YouTubeVideo).where(YouTubeVideo.video_id == video_id)
        )
        return result.scalar_one_or_none()

    async def create_subtitle(
        self,
        session: AsyncSession,
        video_id: str,
        line_number: int,
        start_ms: int,
        end_ms: int,
        text: str,
    ) -> YouTubeSubtitle:
        """Create a single subtitle line.

        Args:
            session: Database session
            video_id: YouTube video ID
            line_number: Sequential line number
            start_ms: Start time in milliseconds
            end_ms: End time in milliseconds
            text: Subtitle text

        Returns:
            Created YouTubeSubtitle instance
        """
        subtitle = YouTubeSubtitle(
            video_id=video_id,
            line_number=line_number,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
        )
        session.add(subtitle)
        await session.flush()
        return subtitle

    async def create_subtitles_batch(
        self,
        session: AsyncSession,
        video_id: str,
        subtitles: list[dict],
    ) -> list[YouTubeSubtitle]:
        """Create multiple subtitle lines in one operation.

        Args:
            session: Database session
            video_id: YouTube video ID
            subtitles: List of dicts with keys: line_number, start_ms, end_ms, text

        Returns:
            List of created YouTubeSubtitle instances
        """
        subtitle_objects = [
            YouTubeSubtitle(
                video_id=video_id,
                line_number=sub["line_number"],
                start_ms=sub["start_ms"],
                end_ms=sub["end_ms"],
                text=sub["text"],
            )
            for sub in subtitles
        ]
        session.add_all(subtitle_objects)
        await session.flush()
        return subtitle_objects

    async def delete_subtitles_for_video(
        self, session: AsyncSession, video_id: str
    ) -> None:
        """Delete all subtitles for a video (used for re-upload).

        Args:
            session: Database session
            video_id: YouTube video ID
        """
        await session.execute(
            sa.delete(YouTubeSubtitle).where(YouTubeSubtitle.video_id == video_id)
        )

    async def get_subtitles_for_video(
        self, session: AsyncSession, video_id: str
    ) -> list[YouTubeSubtitle]:
        """Get all subtitles for a video, ordered by line number.

        Args:
            session: Database session
            video_id: YouTube video ID

        Returns:
            List of YouTubeSubtitle instances
        """
        result = await session.execute(
            sa.select(YouTubeSubtitle)
            .where(YouTubeSubtitle.video_id == video_id)
            .order_by(YouTubeSubtitle.line_number)
        )
        return list(result.scalars().all())
