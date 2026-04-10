"""Create deepl_instances table

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deepl_instances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_lang", sa.Text(), nullable=False),
        sa.Column("target_lang", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_lang", "target_lang"),
    )


def downgrade() -> None:
    op.drop_table("deepl_instances")
