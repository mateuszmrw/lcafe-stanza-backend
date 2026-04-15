"""add youtube tables

Revision ID: 0049
Revises: 0048
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa


revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create youtube_videos table
    op.create_table(
        "youtube_videos",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("video_id", sa.String(11), nullable=False),
        sa.Column("youtube_url", sa.Text(), nullable=False),
        sa.Column("channel_name", sa.String(255), nullable=True),
        sa.Column("video_duration_ms", sa.Integer(), nullable=True),
        sa.Column("subtitle_lang_code", sa.String(5), nullable=True),
        sa.Column("subtitle_source", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["id"], ["content_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", name="uq_youtube_videos_video_id"),
    )
    op.create_index("ix_youtube_videos_video_id", "youtube_videos", ["video_id"])

    # Create youtube_subtitles table
    op.create_table(
        "youtube_subtitles",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("video_id", sa.String(11), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["video_id"], ["youtube_videos.video_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id", "line_number", name="uq_youtube_subtitles_video_line"),
    )
    op.create_index("ix_youtube_subtitles_video", "youtube_subtitles", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_youtube_subtitles_video", table_name="youtube_subtitles")
    op.drop_table("youtube_subtitles")
    op.drop_index("ix_youtube_videos_video_id", table_name="youtube_videos")
    op.drop_table("youtube_videos")
