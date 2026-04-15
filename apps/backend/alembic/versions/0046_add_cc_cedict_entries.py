"""add cc_cedict_entries table

Revision ID: 0046
Revises: 0045
Create Date: 2026-04-15
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cc_cedict_entries",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        # Simplified Chinese (primary lookup key)
        sa.Column("simplified", sa.Text(), nullable=False),
        # Traditional Chinese (alternate lookup key)
        sa.Column("traditional", sa.Text(), nullable=False),
        # Pinyin with tone numbers, e.g. "Zhong1 wen2"
        sa.Column("pinyin", sa.Text(), nullable=False),
        # ["/def1", "/def2", ...] — already split, no leading slash
        sa.Column("glosses", JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "source_dict",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'cc-cedict'"),
        ),
    )
    op.create_index("ix_cc_cedict_simplified", "cc_cedict_entries", ["simplified"])
    op.create_index("ix_cc_cedict_traditional", "cc_cedict_entries", ["traditional"])

    op.execute(
        """
        INSERT INTO dictionary_sources (id, slug, name, description, supported_pairs, priority, is_active)
        VALUES (
            gen_random_uuid(),
            'cc-cedict',
            'CC-CEDICT',
            'CC-CEDICT Chinese–English dictionary (mdbg.net)',
            '[{"source_lang": "zh", "target_lang": "en"}]',
            10,
            true
        )
        ON CONFLICT (slug) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM dictionary_sources WHERE slug = 'cc-cedict'")
    op.drop_index("ix_cc_cedict_traditional", table_name="cc_cedict_entries")
    op.drop_index("ix_cc_cedict_simplified", table_name="cc_cedict_entries")
    op.drop_table("cc_cedict_entries")
