"""add cover_image_path to books

Revision ID: 0055
Revises: 0054
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa


revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column("cover_image_path", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("books", "cover_image_path")
