"""convert words.feats from text to JSONB with backfill

Revision ID: 0062
Revises: 0061
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB


revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("words", sa.Column("feats_jsonb", JSONB, nullable=True))
    conn = op.get_bind()
    batch_size = 10_000
    while True:
        res = conn.execute(text("""
            WITH batch AS (
                SELECT id, feats FROM words
                WHERE feats_jsonb IS NULL AND feats IS NOT NULL AND feats <> ''
                LIMIT :batch
                FOR UPDATE SKIP LOCKED
            )
            UPDATE words SET feats_jsonb = (
                SELECT jsonb_object_agg(split_part(kv, '=', 1), split_part(kv, '=', 2))
                FROM unnest(string_to_array(words.feats, '|')) kv
                WHERE position('=' IN kv) > 0
            )
            FROM batch WHERE words.id = batch.id
            RETURNING words.id
        """), {"batch": batch_size})
        if res.rowcount == 0:
            break
    op.drop_column("words", "feats")
    op.alter_column("words", "feats_jsonb", new_column_name="feats")
    op.create_index("ix_words_feats_gin", "words", ["feats"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_words_feats_gin", "words")
    op.add_column("words", sa.Column("feats_str", sa.Text, nullable=True))
    op.execute("""
        UPDATE words SET feats_str = (
            SELECT string_agg(key || '=' || value, '|')
            FROM jsonb_each_text(feats)
        ) WHERE feats IS NOT NULL
    """)
    op.drop_column("words", "feats")
    op.alter_column("words", "feats_str", new_column_name="feats")
