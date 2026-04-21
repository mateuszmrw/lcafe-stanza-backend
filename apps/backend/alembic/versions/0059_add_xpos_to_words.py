"""add xpos to words

Revision ID: 0059
Revises: 0058
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa


revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "words",
        sa.Column("xpos", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("words", "xpos")
