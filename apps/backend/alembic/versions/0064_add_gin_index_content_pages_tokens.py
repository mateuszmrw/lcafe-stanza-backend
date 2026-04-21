"""add GIN index on content_pages.tokens JSONB for lemma lookups

Revision ID: 0064
Revises: 0063
Create Date: 2026-04-19
"""
from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX idx_content_pages_tokens_gin ON content_pages USING GIN(tokens)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_content_pages_tokens_gin")
