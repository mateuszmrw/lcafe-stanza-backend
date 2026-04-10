"""Create words (vocabulary) table

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "words",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "language_id",
            sa.Integer,
            sa.ForeignKey("languages.id"),
            nullable=False,
        ),
        sa.Column("word", sa.Text, nullable=False),
        sa.Column("lemma", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("pos", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("reading", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'new'")),
        sa.Column("hint", sa.Text),
        sa.Column("tags", ARRAY(sa.Text)),
        sa.Column("lookup_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "language_id", "word"),
    )


def downgrade() -> None:
    op.drop_table("words")
