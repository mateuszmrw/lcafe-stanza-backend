import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class DictCcEntry(Base):
    __tablename__ = "dict_cc_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_word: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source_lang: Mapped[str] = mapped_column(sa.Text, nullable=False)
    target_word: Mapped[str] = mapped_column(sa.Text, nullable=False)
    target_lang: Mapped[str] = mapped_column(sa.Text, nullable=False)
    # POS extracted from {tag} notation — "n", "v", "adj", etc.
    pos: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # Subject area / register notes from [tag] notation
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    source_dict: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'dict.cc'")
    )
