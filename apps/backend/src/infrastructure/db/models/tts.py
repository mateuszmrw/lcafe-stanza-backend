import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class TtsSentenceCache(Base):
    __tablename__ = "tts_sentence_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    language_code: Mapped[str] = mapped_column(sa.Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    audio_file: Mapped[str] = mapped_column(sa.Text, nullable=False)
    duration_ms: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    __table_args__ = (
        sa.UniqueConstraint("language_code", "text_hash", name="uq_tts_sentence_cache"),
    )
