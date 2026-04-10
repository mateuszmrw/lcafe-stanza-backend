"""Make dictionary_entries bilingual: rename language_code→source_lang, add target_lang

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("dictionary_entries", "language_code", new_column_name="source_lang")
    op.add_column(
        "dictionary_entries",
        sa.Column("target_lang", sa.Text, nullable=False, server_default=sa.text("'en'")),
    )
    op.drop_index("ix_dict_word_lang", table_name="dictionary_entries")
    op.create_index(
        "ix_dict_word_bilingual",
        "dictionary_entries",
        ["word", "source_lang", "target_lang"],
    )


def downgrade() -> None:
    op.drop_index("ix_dict_word_bilingual", table_name="dictionary_entries")
    op.create_index("ix_dict_word_lang", "dictionary_entries", ["word", "source_lang"])
    op.drop_column("dictionary_entries", "target_lang")
    op.alter_column("dictionary_entries", "source_lang", new_column_name="language_code")
