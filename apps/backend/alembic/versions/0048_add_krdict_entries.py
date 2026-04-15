"""add krdict_entries table

Revision ID: 0048
Revises: 0047
Create Date: 2026-04-15
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "krdict_entries",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        # Korean headword (lowercased)
        sa.Column("word", sa.Text(), nullable=False),
        # Hanja (Chinese character) representation, e.g. "家族"
        sa.Column("hanja", sa.Text(), nullable=True),
        # Normalised part of speech: noun, verb, adjective, adverb, …
        sa.Column("pos", sa.Text(), nullable=True),
        # Vocabulary level: beginner | intermediate | advanced
        sa.Column("level", sa.Text(), nullable=True),
        # [{text, en, examples: [str]}] — Korean definition + optional English
        sa.Column("definitions", JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "source_dict",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'krdict'"),
        ),
    )
    op.create_index("ix_krdict_word", "krdict_entries", ["word"])

    op.execute(
        """
        INSERT INTO dictionary_sources (id, slug, name, description, supported_pairs, priority, is_active)
        VALUES (
            gen_random_uuid(),
            'krdict',
            'KRDICT',
            'Korean Basic Dictionary (한국어기초사전) by NIKL',
            '[{"source_lang": "ko", "target_lang": "en"}]',
            10,
            true
        )
        ON CONFLICT (slug) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM dictionary_sources WHERE slug = 'krdict'")
    op.drop_index("ix_krdict_word", table_name="krdict_entries")
    op.drop_table("krdict_entries")
