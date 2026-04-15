import uuid
from datetime import UTC, datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class ContentItem(Base):
    __tablename__ = "content_items"

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
    type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    title: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text)
    word_count: Mapped[Optional[int]] = mapped_column(sa.Integer)
    status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'pending'")
    )
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text)
    register: Mapped[Optional[str]] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=lambda: datetime.now(UTC),
    )


class Book(Base):
    __tablename__ = "books"

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("content_items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    file_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    file_path: Mapped[str] = mapped_column(sa.Text, nullable=False)
    chapter_count: Mapped[Optional[int]] = mapped_column(sa.Integer)
    audio_file_path: Mapped[Optional[str]] = mapped_column(sa.Text)
    audio_duration_ms: Mapped[Optional[int]] = mapped_column(sa.Integer)
    alignment_status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'none'")
    )
    has_audio_overlay: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    audio_overlay_status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'none'")
    )
    tts_status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'none'")
    )


class ContentPage(Base):
    __tablename__ = "content_pages"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    chapter_number: Mapped[Optional[int]] = mapped_column(sa.Integer)
    chapter_name: Mapped[Optional[str]] = mapped_column(sa.Text)
    chapter_page_number: Mapped[Optional[int]] = mapped_column(sa.Integer)
    xhtml_file: Mapped[Optional[str]] = mapped_column(sa.Text)
    tts_manifest_path: Mapped[Optional[str]] = mapped_column(sa.Text)
    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    lemma_map: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'pending'")
    )

    __table_args__ = (sa.UniqueConstraint("content_item_id", "page_number"),)
