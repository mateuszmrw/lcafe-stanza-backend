"""Add feats column to words table

Revision ID: 0016
Revises: 0015
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "words",
        sa.Column(
            "feats",
            sa.Text,
            nullable=False,
            server_default=sa.text("''"),
        ),
    )


def downgrade() -> None:
    op.drop_column("words", "feats")
