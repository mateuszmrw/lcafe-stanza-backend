"""Create providers table with seed data

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("slug", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_builtin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint("type", "slug"),
    )

    op.execute(
        """
        INSERT INTO providers (type, slug, name, description, is_builtin) VALUES
          ('nlp',         'stanza',     'Stanza',             'Stanza NLP pipeline (tokenize, POS, lemma)',                    true),
          ('nlp',         'spacy',      'SpaCy Transformers', 'SpaCy transformer models (stub — not yet implemented)',          true),
          ('translation', 'deepl',      'DeepL',              'DeepL translation API (BYOK)',                                  true),
          ('dictionary',  'wiktionary', 'Wiktionary',         'Wiktionary local database (kaikki.org JSONL dumps)',            true)
        """
    )


def downgrade() -> None:
    op.drop_table("providers")
