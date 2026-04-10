import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(sa.Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    flag_emoji: Mapped[Optional[str]] = mapped_column(sa.Text)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )


class LanguageNlpConfig(Base):
    __tablename__ = "language_nlp_config"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    language_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("languages.id"),
        unique=True,
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("providers.id"),
        nullable=False,
    )
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
