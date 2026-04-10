"""Create content_items, books, and content_pages tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_items",
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
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("word_count", sa.Integer),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("error_message", sa.Text),
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
    )

    op.create_table(
        "books",
        sa.Column(
            "content_item_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("file_hash", sa.Text, nullable=False),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("chapter_count", sa.Integer),
    )

    op.create_table(
        "content_pages",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "content_item_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("chapter_number", sa.Integer),
        sa.Column("chapter_name", sa.Text),
        sa.Column("chapter_page_number", sa.Integer),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("tokens", JSONB),
        sa.UniqueConstraint("content_item_id", "page_number"),
    )


def downgrade() -> None:
    op.drop_table("content_pages")
    op.drop_table("books")
    op.drop_table("content_items")
