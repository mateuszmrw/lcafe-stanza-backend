"""Backfill content_pages.status for already-completed books

Migration 0009 added status='pending' as the default for all pages.
Pages that belonged to completed books already had their words tokenized,
so they should be marked 'ready' rather than left as 'pending'.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-09
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE content_pages cp
        SET status = 'ready'
        FROM content_items ci
        WHERE cp.content_item_id = ci.id
          AND ci.status = 'completed'
        """
    )


def downgrade() -> None:
    # Reverting to 'pending' is safe — no data loss, just loses the backfill.
    op.execute(
        """
        UPDATE content_pages cp
        SET status = 'pending'
        FROM content_items ci
        WHERE cp.content_item_id = ci.id
          AND ci.status = 'completed'
        """
    )
