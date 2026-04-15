"""Create daily_activity table

Revision ID: 0036
Revises: 0035
Create Date: 2026-04-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_activity",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer, sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("pages_read", sa.Integer, nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_daily_activity_user_language_date", "daily_activity", ["user_id", "language_id", "date"])
    op.create_unique_constraint(
        "uq_daily_activity",
        "daily_activity",
        ["user_id", "language_id", "date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_daily_activity", "daily_activity", type_="unique")
    op.drop_index("ix_daily_activity_user_language_date", table_name="daily_activity")
    op.drop_table("daily_activity")
