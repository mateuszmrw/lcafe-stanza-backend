import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class WordFrequency(Base):
    __tablename__ = "word_frequencies"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    language_code: Mapped[str] = mapped_column(sa.Text, nullable=False)
    lemma: Mapped[str] = mapped_column(sa.Text, nullable=False)
    rank: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    per_million: Mapped[float | None] = mapped_column(sa.Float, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("language_code", "lemma", name="uq_freq_language_lemma"),
        sa.Index("ix_freq_language_lemma", "language_code", "lemma"),
    )
