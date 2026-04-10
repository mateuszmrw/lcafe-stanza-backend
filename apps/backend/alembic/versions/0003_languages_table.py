"""Create languages table with seed data

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "languages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.Text, unique=True, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("flag_emoji", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )

    op.execute(
        """
        INSERT INTO languages (code, name, flag_emoji) VALUES
          ('en', 'English',  '🇬🇧'),
          ('ru', 'Russian',  '🇷🇺'),
          ('de', 'German',   '🇩🇪'),
          ('fr', 'French',   '🇫🇷'),
          ('pl', 'Polish',   '🇵🇱'),
          ('ja', 'Japanese', '🇯🇵'),
          ('zh', 'Chinese',  '🇨🇳'),
          ('es', 'Spanish',  '🇪🇸')
        """
    )


def downgrade() -> None:
    op.drop_table("languages")
