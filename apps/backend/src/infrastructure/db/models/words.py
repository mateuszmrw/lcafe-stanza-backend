import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class Word(Base):
    __tablename__ = "words"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    language_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("languages.id"), nullable=False
    )
    word: Mapped[str] = mapped_column(sa.Text, nullable=False)
    lemma: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("''")
    )
    pos: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("''")
    )
    reading: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("''")
    )
    gender: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("''")
    )
    feats: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("''")
    )
    dep_head: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    dep_rel: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("''")
    )
    status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'new'")
    )
    hint: Mapped[Optional[str]] = mapped_column(sa.Text)
    sentence_context: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(sa.Text))
    lookup_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    anki_pending: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    __table_args__ = (sa.UniqueConstraint("user_id", "language_id", "word"),)
