"""Default auto_ignore_proper_nouns to true

Revision ID: 0033
Revises: 0032
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "auto_ignore_proper_nouns",
        server_default=sa.text("true"),
    )
    op.execute("UPDATE users SET auto_ignore_proper_nouns = true")


def downgrade() -> None:
    op.alter_column(
        "users",
        "auto_ignore_proper_nouns",
        server_default=sa.text("false"),
    )
