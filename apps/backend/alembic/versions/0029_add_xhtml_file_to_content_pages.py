"""add xhtml_file to content_pages

Revision ID: 0029
Revises: 0028
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "content_pages",
        sa.Column("xhtml_file", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_pages", "xhtml_file")
