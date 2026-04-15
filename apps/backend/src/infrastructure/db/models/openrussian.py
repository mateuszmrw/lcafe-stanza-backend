import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class OpenRussianWord(Base):
    __tablename__ = "openrussian_words"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Original OpenRussian numeric ID (kept for reference / deduplication)
    word_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    # Bare form without stress marks — used as the lookup key
    bare: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # Form with Unicode stress marks, e.g. "говори́ть"
    accented: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Lowercase POS tag from OpenRussian ("noun", "verb", "adj", ...)
    pos: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="")
    # Frequency rank (lower = more common); null if not in OpenRussian frequency list
    rank: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    # Verbal aspect: "perfective" | "imperfective" | None
    aspect: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # [{"text": str, "info": str|None, "example_ru": str|None, "example_tl": str|None}]
    glosses: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    # [{"form_type": str, "form1": str|None, "form2": str|None}]
    forms: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    source_dict: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'openrussian'")
    )
