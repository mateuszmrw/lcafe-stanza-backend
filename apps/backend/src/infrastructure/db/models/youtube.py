"""ORM models for YouTube video imports."""
import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class YouTubeVideo(Base):
    """Store metadata about imported YouTube videos."""

    __tablename__ = "youtube_videos"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("content_items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    video_id: Mapped[str] = mapped_column(
        sa.String(11), nullable=False, unique=True, index=True
    )
    youtube_url: Mapped[str] = mapped_column(sa.Text, nullable=False)
    channel_name: Mapped[Optional[str]] = mapped_column(sa.String(255))
    video_duration_ms: Mapped[Optional[int]] = mapped_column(sa.Integer)
    subtitle_lang_code: Mapped[Optional[str]] = mapped_column(sa.String(5))
    subtitle_source: Mapped[Optional[str]] = mapped_column(sa.String(50))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )


class YouTubeSubtitle(Base):
    """Store subtitle lines for YouTube videos."""

    __tablename__ = "youtube_subtitles"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    video_id: Mapped[str] = mapped_column(
        sa.String(11),
        sa.ForeignKey("youtube_videos.video_id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    __table_args__ = (
        sa.UniqueConstraint("video_id", "line_number", name="uq_youtube_subtitles_video_line"),
        sa.Index("ix_youtube_subtitles_video", "video_id"),
    )
