"""add skip_in_vocabulary to words

Revision ID: 0057
Revises: 0056
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa


revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "words",
        sa.Column(
            "skip_in_vocabulary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("words", "skip_in_vocabulary")
