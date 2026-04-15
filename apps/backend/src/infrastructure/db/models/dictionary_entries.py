import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class DictionaryEntry(Base):
    __tablename__ = "dictionary_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    word: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source_lang: Mapped[str] = mapped_column(sa.Text, nullable=False)
    target_lang: Mapped[str] = mapped_column(sa.Text, nullable=False)
    pos: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    glosses: Mapped[list] = mapped_column(sa.JSON, nullable=False, default=list)
    forms: Mapped[list] = mapped_column(sa.JSON, nullable=False, default=list)
    etymology: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    labels: Mapped[list] = mapped_column(sa.JSON, nullable=False, default=list)
    source_dict: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'wiktionary'")
    )

    __table_args__ = (
        sa.Index("ix_dict_word_bilingual", "word", "source_lang", "target_lang", "source_dict"),
    )
