"""add openrussian_words table

Revision ID: 0045
Revises: 0044
Create Date: 2026-04-15
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "openrussian_words",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("word_id", sa.Integer(), nullable=True),
        sa.Column("bare", sa.Text(), nullable=False),
        sa.Column("accented", sa.Text(), nullable=True),
        sa.Column("pos", sa.Text(), nullable=False, server_default=""),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("aspect", sa.Text(), nullable=True),
        sa.Column("glosses", JSONB(), nullable=False, server_default="[]"),
        sa.Column("forms", JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "source_dict",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'openrussian'"),
        ),
    )
    op.create_index("ix_openrussian_bare", "openrussian_words", ["bare"])

    # Seed dictionary_sources row for OpenRussian (priority=10 > Wiktionary's 5)
    op.execute(
        """
        INSERT INTO dictionary_sources (id, slug, name, description, supported_pairs, priority, is_active)
        VALUES (
            gen_random_uuid(),
            'openrussian',
            'OpenRussian',
            'OpenRussian.org — Russian → English with morphology and stress marks',
            '[{"source_lang": "ru", "target_lang": "en"}]',
            10,
            true
        )
        ON CONFLICT (slug) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM dictionary_sources WHERE slug = 'openrussian'")
    op.drop_index("ix_openrussian_bare", table_name="openrussian_words")
    op.drop_table("openrussian_words")
