"""Create sentence_alignments table

Revision ID: 0027
Revises: 0026
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sentence_alignments",
        sa.Column(
            "id",
            sa.UUID,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "page_id",
            sa.UUID,
            sa.ForeignKey("content_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sentence_index", sa.Integer, nullable=False),
        sa.Column("audio_start_ms", sa.Integer, nullable=False),
        sa.Column("audio_end_ms", sa.Integer, nullable=False),
        sa.UniqueConstraint("page_id", "sentence_index", name="uq_sentence_alignment"),
    )
    op.create_index(
        "ix_sentence_alignments_page_id",
        "sentence_alignments",
        ["page_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_sentence_alignments_page_id", table_name="sentence_alignments")
    op.drop_table("sentence_alignments")
