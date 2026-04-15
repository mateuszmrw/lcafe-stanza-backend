"""Move proficiency_level to per-language user_language_profiles table

Revision ID: 0030
Revises: 0029
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_language_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "language_id",
            sa.Integer,
            sa.ForeignKey("languages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proficiency_level", sa.Text, nullable=True),
        sa.UniqueConstraint("user_id", "language_id"),
    )

    # Migrate existing proficiency data for users who have both set
    op.execute(
        """
        INSERT INTO user_language_profiles (user_id, language_id, proficiency_level)
        SELECT id, active_language_id, proficiency_level
        FROM users
        WHERE active_language_id IS NOT NULL
          AND proficiency_level IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    op.drop_column("users", "proficiency_level")


def downgrade() -> None:
    op.add_column("users", sa.Column("proficiency_level", sa.Text, nullable=True))

    # Best-effort restore: pull from the profile for each user's current active language
    op.execute(
        """
        UPDATE users u
        SET proficiency_level = ulp.proficiency_level
        FROM user_language_profiles ulp
        WHERE ulp.user_id = u.id
          AND ulp.language_id = u.active_language_id
        """
    )

    op.drop_table("user_language_profiles")
