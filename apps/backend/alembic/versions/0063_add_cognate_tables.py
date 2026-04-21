"""add cognate_pairs and cognate_language_pairs tables

Revision ID: 0063
Revises: 0062
Create Date: 2026-04-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cognate_pairs",
        sa.Column("l1_lemma", sa.Text, nullable=False),
        sa.Column("l1_language", sa.String(8), nullable=False),
        sa.Column("l2_lemma", sa.Text, nullable=False),
        sa.Column("l2_language", sa.String(8), nullable=False),
        sa.Column("cognate_type", sa.String(16), nullable=False),
        sa.Column("similarity_score", sa.Float, nullable=True),
        sa.Column("semantic_score", sa.Float, nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("l1_meaning", sa.Text, nullable=True),
        sa.Column("l2_meaning", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("l1_lemma", "l1_language", "l2_lemma", "l2_language"),
    )
    op.create_index(
        "idx_cognate_l2_lookup",
        "cognate_pairs",
        ["l2_lemma", "l2_language", "l1_language"],
    )

    op.create_table(
        "cognate_language_pairs",
        sa.Column("l2_language", sa.String(8), nullable=False),
        sa.Column("supported_l1_codes", ARRAY(sa.Text), nullable=False),
        sa.Column("last_imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("l2_language"),
    )
    op.execute("INSERT INTO cognate_language_pairs (l2_language, supported_l1_codes) VALUES ('ru', ARRAY['pl'])")


def downgrade() -> None:
    op.drop_table("cognate_language_pairs")
    op.drop_index("idx_cognate_l2_lookup", table_name="cognate_pairs")
    op.drop_table("cognate_pairs")
