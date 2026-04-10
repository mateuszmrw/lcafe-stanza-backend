"""Create word_frequencies table

Revision ID: 0022
Revises: 0021
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "word_frequencies",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("language_code", sa.Text, nullable=False),
        sa.Column("lemma", sa.Text, nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("per_million", sa.Float, nullable=True),
        sa.UniqueConstraint("language_code", "lemma", name="uq_freq_language_lemma"),
    )
    op.create_index("ix_freq_language_lemma", "word_frequencies", ["language_code", "lemma"])


def downgrade() -> None:
    op.drop_index("ix_freq_language_lemma", table_name="word_frequencies")
    op.drop_table("word_frequencies")
