"""add ent_type to words

Revision ID: 0056
Revises: 0055
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa


revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "words",
        sa.Column("ent_type", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("words", "ent_type")
