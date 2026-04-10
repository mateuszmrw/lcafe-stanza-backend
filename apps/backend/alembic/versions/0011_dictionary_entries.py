"""Create dictionary_entries table for local Wiktionary storage

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dictionary_entries",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("word", sa.Text, nullable=False),
        sa.Column("language_code", sa.Text, nullable=False),
        sa.Column("pos", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("glosses", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("forms", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("etymology", sa.Text),
    )
    op.create_index("ix_dict_word_lang", "dictionary_entries", ["word", "language_code"])


def downgrade() -> None:
    op.drop_index("ix_dict_word_lang", "dictionary_entries")
    op.drop_table("dictionary_entries")
