from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class CognatePair(Base):
    __tablename__ = "cognate_pairs"

    l1_lemma: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    l1_language: Mapped[str] = mapped_column(sa.String(8), primary_key=True)
    l2_lemma: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    l2_language: Mapped[str] = mapped_column(sa.String(8), primary_key=True)
    cognate_type: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    similarity_score: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    semantic_score: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    source: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    l1_meaning: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    l2_meaning: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)


class CognateLanguagePair(Base):
    __tablename__ = "cognate_language_pairs"

    l2_language: Mapped[str] = mapped_column(sa.String(8), primary_key=True)
    supported_l1_codes: Mapped[list[str]] = mapped_column(ARRAY(sa.Text), nullable=False)
    last_imported_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
