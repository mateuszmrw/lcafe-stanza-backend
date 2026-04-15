"""Add TTS support: tts_sentence_cache, books.tts_status, content_pages.tts_manifest_path

Revision ID: 0034
Revises: 0033
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tts_sentence_cache",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("language_code", sa.Text, nullable=False),
        sa.Column("text_hash", sa.Text, nullable=False),
        sa.Column("audio_file", sa.Text, nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("language_code", "text_hash", name="uq_tts_sentence_cache"),
    )

    op.add_column(
        "books",
        sa.Column(
            "tts_status",
            sa.Text,
            nullable=False,
            server_default=sa.text("'none'"),
        ),
    )

    op.add_column(
        "content_pages",
        sa.Column("tts_manifest_path", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_pages", "tts_manifest_path")
    op.drop_column("books", "tts_status")
    op.drop_table("tts_sentence_cache")
