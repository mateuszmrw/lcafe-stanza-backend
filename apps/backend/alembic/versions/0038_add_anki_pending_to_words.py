"""Add anki_pending column to words

Revision ID: 0038
Revises: 0037
Create Date: 2026-04-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "words",
        sa.Column("anki_pending", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("words", "anki_pending")
