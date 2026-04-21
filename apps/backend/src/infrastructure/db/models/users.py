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
    native_language_code: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    auto_ignore_proper_nouns: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    token_version: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(sa.Text)
    exercise_interval_pages: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("5")
    )
    exercises_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )


class UserLanguageProfile(Base):
    __tablename__ = "user_language_profiles"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    language_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("languages.id", ondelete="CASCADE"),
        nullable=False,
    )
    proficiency_level: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    native_language_code: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    auto_ignore_proper_nouns: Mapped[Optional[bool]] = mapped_column(sa.Boolean, nullable=True)
    coref_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    __table_args__ = (sa.UniqueConstraint("user_id", "language_id"),)
