"""add dict_cc_entries table

Revision ID: 0047
Revises: 0046
Create Date: 2026-04-15
"""
import sqlalchemy as sa
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dict_cc_entries",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_word", sa.Text(), nullable=False),
        sa.Column("source_lang", sa.Text(), nullable=False),
        sa.Column("target_word", sa.Text(), nullable=False),
        sa.Column("target_lang", sa.Text(), nullable=False),
        # Part-of-speech extracted from {tag} notation, e.g. "n", "v", "adj"
        sa.Column("pos", sa.Text(), nullable=True),
        # Subject area / register notes extracted from [tag] notation
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "source_dict",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'dict.cc'"),
        ),
    )
    op.create_index(
        "ix_dict_cc_source_word",
        "dict_cc_entries",
        ["source_word", "source_lang", "target_lang"],
    )
    op.create_index(
        "ix_dict_cc_target_word",
        "dict_cc_entries",
        ["target_word", "target_lang", "source_lang"],
    )

    op.execute(
        """
        INSERT INTO dictionary_sources (id, slug, name, description, supported_pairs, priority, is_active)
        VALUES (
            gen_random_uuid(),
            'dict.cc',
            'dict.cc',
            'dict.cc community bilingual dictionary (multiple language pairs)',
            '[]',
            8,
            true
        )
        ON CONFLICT (slug) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM dictionary_sources WHERE slug = 'dict.cc'")
    op.drop_index("ix_dict_cc_target_word", table_name="dict_cc_entries")
    op.drop_index("ix_dict_cc_source_word", table_name="dict_cc_entries")
    op.drop_table("dict_cc_entries")
