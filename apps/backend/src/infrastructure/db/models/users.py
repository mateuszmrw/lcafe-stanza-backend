import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(sa.Text, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(sa.Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    role: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'user'")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    active_language_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer, sa.ForeignKey("languages.id", ondelete="SET NULL"), nullable=True
    )
    proficiency_level: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    native_language_code: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
