"""Add model column to system_api_keys

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "system_api_keys",
        sa.Column("model", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("system_api_keys", "model")
