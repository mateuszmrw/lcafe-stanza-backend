"""Add gender to words, drop tokens from content_pages

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "words",
        sa.Column("gender", sa.Text, nullable=False, server_default=sa.text("''")),
    )
    op.add_column(
        "content_pages",
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'pending'")),
    )
    op.drop_column("content_pages", "tokens")


def downgrade() -> None:
    op.add_column(
        "content_pages",
        sa.Column("tokens", postgresql.JSONB(), nullable=True),
    )
    op.drop_column("content_pages", "status")
    op.drop_column("words", "gender")
