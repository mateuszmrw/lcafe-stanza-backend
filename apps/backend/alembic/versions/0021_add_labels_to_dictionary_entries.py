"""Add labels column to dictionary_entries

Revision ID: 0021
Revises: 0020
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dictionary_entries",
        sa.Column("labels", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("dictionary_entries", "labels")
