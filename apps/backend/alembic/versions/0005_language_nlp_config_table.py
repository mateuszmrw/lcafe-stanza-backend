"""Create language_nlp_config table with default Stanza seed

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "language_nlp_config",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "language_id",
            sa.Integer,
            sa.ForeignKey("languages.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "provider_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("providers.id"),
            nullable=False,
        ),
        sa.Column(
            "config",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Seed: default NLP config for all seed languages — Stanza with full language name
    op.execute(
        """
        INSERT INTO language_nlp_config (language_id, provider_id, config)
        SELECT l.id, p.id, jsonb_build_object('stanza_language_name', lower(l.name))
        FROM languages l
        CROSS JOIN providers p
        WHERE p.slug = 'stanza' AND p.type = 'nlp'
        """
    )


def downgrade() -> None:
    op.drop_table("language_nlp_config")
