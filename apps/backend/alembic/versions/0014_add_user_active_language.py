"""Add active_language_id to users table

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "active_language_id",
            sa.Integer,
            sa.ForeignKey("languages.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "active_language_id")
