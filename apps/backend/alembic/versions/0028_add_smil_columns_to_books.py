"""Add SMIL audio overlay columns to books

Revision ID: 0028
Revises: 0027
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column(
            "has_audio_overlay",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "books",
        sa.Column(
            "audio_overlay_status",
            sa.Text,
            nullable=False,
            server_default=sa.text("'none'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("books", "audio_overlay_status")
    op.drop_column("books", "has_audio_overlay")
