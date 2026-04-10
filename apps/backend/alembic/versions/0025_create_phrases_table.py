"""Create phrases table

Revision ID: 0025
Revises: 0024
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phrases",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer, sa.ForeignKey("languages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("translation", sa.Text, nullable=True),
        sa.Column("context", sa.Text, nullable=True),
        sa.Column("book_id", sa.UUID, sa.ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("page", sa.Integer, nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'learning'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_phrases_user_language", "phrases", ["user_id", "language_id"])


def downgrade() -> None:
    op.drop_index("ix_phrases_user_language", table_name="phrases")
    op.drop_table("phrases")
