import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class SavedSentence(Base):
    __tablename__ = "saved_sentences"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("content_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    language_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False
    )
    sentence_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    sentence_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    __table_args__ = (
        sa.UniqueConstraint("user_id", "book_id", "sentence_index", name="uq_saved_sentence"),
    )
