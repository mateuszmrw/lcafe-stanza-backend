"""Add dep_head and dep_rel columns to words

Revision ID: 0020
Revises: 0019
Create Date: 2026-04-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("words", sa.Column("dep_head", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("words", sa.Column("dep_rel", sa.Text(), nullable=False, server_default="''"))


def downgrade() -> None:
    op.drop_column("words", "dep_rel")
    op.drop_column("words", "dep_head")
