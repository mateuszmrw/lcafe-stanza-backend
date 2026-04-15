import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class SentenceAlignment(Base):
    __tablename__ = "sentence_alignments"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("content_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    sentence_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    audio_start_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    audio_end_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    audio_file: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("page_id", "sentence_index", name="uq_sentence_alignment"),
    )
