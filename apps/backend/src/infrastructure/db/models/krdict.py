import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class KrdictEntry(Base):
    __tablename__ = "krdict_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    word: Mapped[str] = mapped_column(sa.Text, nullable=False)
    hanja: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    pos: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    level: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # [{text: str, en: str|None, examples: [str]}]
    definitions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    source_dict: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'krdict'")
    )
