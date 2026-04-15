"""add sentence_context to words

Revision ID: 0031
Revises: 0030
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("words", sa.Column("sentence_context", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("words", "sentence_context")
