"""Add Korean to languages table

Revision ID: 0023
Revises: 0022
Create Date: 2026-04-10
"""

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO languages (code, name, flag_emoji)
        VALUES ('ko', 'Korean', '🇰🇷')
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM languages WHERE code = 'ko'")
