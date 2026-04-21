"""add coref_enabled to user_language_profiles

Revision ID: 0060
Revises: 0059
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa


revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_language_profiles",
        sa.Column(
            "coref_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_language_profiles", "coref_enabled")
