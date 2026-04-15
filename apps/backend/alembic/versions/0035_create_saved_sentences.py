"""Create saved_sentences table

Revision ID: 0035
Revises: 0034
Create Date: 2026-04-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_sentences",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", sa.UUID, sa.ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("language_id", sa.Integer, sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sentence_index", sa.Integer, nullable=False),
        sa.Column("sentence_text", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_saved_sentences_user_language", "saved_sentences", ["user_id", "language_id"])
    op.create_unique_constraint(
        "uq_saved_sentence",
        "saved_sentences",
        ["user_id", "book_id", "sentence_index"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_saved_sentence", "saved_sentences", type_="unique")
    op.drop_index("ix_saved_sentences_user_language", table_name="saved_sentences")
    op.drop_table("saved_sentences")
