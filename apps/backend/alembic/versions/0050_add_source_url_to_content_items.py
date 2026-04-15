"""add source_url to content_items

Revision ID: 0050
Revises: 0049
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa


revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_items", sa.Column("source_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("content_items", "source_url")
