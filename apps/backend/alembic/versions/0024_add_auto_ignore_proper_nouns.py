"""Add auto_ignore_proper_nouns to users

Revision ID: 0024
Revises: 0023
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "auto_ignore_proper_nouns",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "auto_ignore_proper_nouns")
