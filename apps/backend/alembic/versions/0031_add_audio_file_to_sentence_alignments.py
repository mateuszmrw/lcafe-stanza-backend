"""Add audio_file column to sentence_alignments

Revision ID: 0031
Revises: 0030
Create Date: 2026-04-14

Stores the storage-relative path to the audio file for each alignment row.
Required for EPUB3 SMIL books that have one audio file per chapter.
"""

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sentence_alignments",
        sa.Column("audio_file", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sentence_alignments", "audio_file")
