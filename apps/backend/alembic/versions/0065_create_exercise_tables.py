"""Create exercise_attempts and exercise_progress tables

Revision ID: 0065
Revises: 0064
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa


revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create exercise_attempts table
    op.create_table(
        "exercise_attempts",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("word_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("content_item_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("exercise_type", sa.String(32), nullable=False),
        sa.Column("correct", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_item_id"], ["content_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exercise_attempts_user_word",
        "exercise_attempts",
        ["user_id", "word_id"],
    )
    op.create_index(
        "ix_exercise_attempts_user_content_created",
        "exercise_attempts",
        ["user_id", "content_item_id", "created_at"],
    )

    # Create exercise_progress table
    op.create_table(
        "exercise_progress",
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("content_item_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("last_exercise_page", sa.Integer, nullable=False, server_default="0"),
        sa.Column("snooze_until_page", sa.Integer, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_item_id"], ["content_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "content_item_id"),
    )


def downgrade() -> None:
    op.drop_table("exercise_progress")
    op.drop_index("ix_exercise_attempts_user_content_created", table_name="exercise_attempts")
    op.drop_index("ix_exercise_attempts_user_word", table_name="exercise_attempts")
    op.drop_table("exercise_attempts")
