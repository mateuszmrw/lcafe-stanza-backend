"""Add proficiency_level and native_language_code to users table

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("proficiency_level", sa.Text, nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("native_language_code", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "native_language_code")
    op.drop_column("users", "proficiency_level")
