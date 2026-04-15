"""add dictionary_sources table and source_dict column

Revision ID: 0044
Revises: 0043
Create Date: 2026-04-15
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add source_dict to dictionary_entries (default = 'wiktionary')
    op.add_column(
        "dictionary_entries",
        sa.Column(
            "source_dict",
            sa.Text(),
            nullable=False,
            server_default="wiktionary",
        ),
    )

    # 2. Drop old index, recreate with source_dict included
    op.drop_index("ix_dict_word_bilingual", table_name="dictionary_entries")
    op.create_index(
        "ix_dict_word_bilingual",
        "dictionary_entries",
        ["word", "source_lang", "target_lang", "source_dict"],
    )

    # 3. Create dictionary_sources metadata table
    op.create_table(
        "dictionary_sources",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("supported_pairs", JSONB(), nullable=False, server_default="[]"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("slug", name="uq_dictionary_sources_slug"),
    )

    # 4. Seed the Wiktionary row
    op.execute(
        """
        INSERT INTO dictionary_sources (id, slug, name, description, supported_pairs, priority, is_active)
        VALUES (
            gen_random_uuid(),
            'wiktionary',
            'Wiktionary',
            'Kaikki.org Wiktionary extract — bilingual JSONL format',
            '[]',
            5,
            true
        )
        """
    )


def downgrade() -> None:
    op.drop_table("dictionary_sources")

    op.drop_index("ix_dict_word_bilingual", table_name="dictionary_entries")
    op.drop_column("dictionary_entries", "source_dict")
    op.create_index(
        "ix_dict_word_bilingual",
        "dictionary_entries",
        ["word", "source_lang", "target_lang"],
    )
