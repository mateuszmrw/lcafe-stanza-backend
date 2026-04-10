import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class Phrase(Base):
    __tablename__ = "phrases"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    language_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer, sa.ForeignKey("languages.id", ondelete="SET NULL"), nullable=True
    )
    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    translation: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    context: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("content_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    page: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'learning'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    __table_args__ = (
        sa.Index("ix_phrases_user_language", "user_id", "language_id"),
    )
