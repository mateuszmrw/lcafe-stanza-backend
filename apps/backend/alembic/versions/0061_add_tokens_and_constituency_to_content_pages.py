"""add tokens and constituency to content_pages

Revision ID: 0061
Revises: 0060
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_pages",
        sa.Column("tokens", JSONB, nullable=True),
    )
    op.add_column(
        "content_pages",
        sa.Column("constituency", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_pages", "constituency")
    op.drop_column("content_pages", "tokens")
