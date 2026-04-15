"""Add register column to content_items

Revision ID: 0032
Revises: 0031
Create Date: 2026-04-14

Values: 'formal' | 'literary' | 'informal' | 'technical' | NULL
Used to enrich grammar explanations with document register context.
"""

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_items",
        sa.Column("register", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_items", "register")
