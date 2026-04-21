import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    word_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("words.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    correct: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )


class ExerciseProgress(Base):
    __tablename__ = "exercise_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    last_exercise_page: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    snooze_until_page: Mapped[Optional[int]] = mapped_column(
        sa.Integer, nullable=True
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint("user_id", "content_item_id"),
    )
