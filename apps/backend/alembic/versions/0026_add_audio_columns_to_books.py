"""Add audio columns to books

Revision ID: 0026
Revises: 0025
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("books", sa.Column("audio_file_path", sa.Text, nullable=True))
    op.add_column("books", sa.Column("audio_duration_ms", sa.Integer, nullable=True))
    op.add_column(
        "books",
        sa.Column(
            "alignment_status",
            sa.Text,
            nullable=False,
            server_default=sa.text("'none'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("books", "alignment_status")
    op.drop_column("books", "audio_duration_ms")
    op.drop_column("books", "audio_file_path")
