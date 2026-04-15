"""Add native_language_code and auto_ignore_proper_nouns to user_language_profiles

Revision ID: 0039
Revises: 0038
Create Date: 2026-04-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_language_profiles",
        sa.Column("native_language_code", sa.Text, nullable=True),
    )
    op.add_column(
        "user_language_profiles",
        sa.Column("auto_ignore_proper_nouns", sa.Boolean, nullable=True),
    )

    # Migrate existing global values into each user's language profiles
    op.execute(
        """
        UPDATE user_language_profiles ulp
        SET native_language_code = u.native_language_code,
            auto_ignore_proper_nouns = u.auto_ignore_proper_nouns
        FROM users u
        WHERE ulp.user_id = u.id
        """
    )


def downgrade() -> None:
    op.drop_column("user_language_profiles", "auto_ignore_proper_nouns")
    op.drop_column("user_language_profiles", "native_language_code")
