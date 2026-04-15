import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class CcCedictEntry(Base):
    __tablename__ = "cc_cedict_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    simplified: Mapped[str] = mapped_column(sa.Text, nullable=False)
    traditional: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # Tone-number pinyin, e.g. "Zhong1 wen2"
    pinyin: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # Plain English definitions (slashes already stripped)
    glosses: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    source_dict: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'cc-cedict'")
    )
