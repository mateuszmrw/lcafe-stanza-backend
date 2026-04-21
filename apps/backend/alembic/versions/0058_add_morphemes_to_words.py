"""add morphemes to words

Revision ID: 0058
Revises: 0057
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "words",
        sa.Column("morphemes", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("words", "morphemes")
