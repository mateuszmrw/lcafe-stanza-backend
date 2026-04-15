"""add source_page_id and source_sentence_index to words

Revision ID: 0051
Revises: 0050
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa


revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "words",
        sa.Column("source_page_id", sa.UUID(as_uuid=True), sa.ForeignKey("content_pages.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "words",
        sa.Column("source_sentence_index", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("words", "source_sentence_index")
    op.drop_column("words", "source_page_id")
