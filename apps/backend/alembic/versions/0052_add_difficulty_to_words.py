"""add exposure_count and difficulty_score to words

Revision ID: 0052
Revises: 0051
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa


revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "words",
        sa.Column("exposure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "words",
        sa.Column("difficulty_score", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("words", "difficulty_score")
    op.drop_column("words", "exposure_count")
