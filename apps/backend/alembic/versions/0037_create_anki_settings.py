"""Create anki_settings table

Revision ID: 0037
Revises: 0036
Create Date: 2026-04-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anki_settings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("anki_connect_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("anki_settings")
