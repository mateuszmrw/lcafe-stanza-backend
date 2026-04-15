import uuid
from datetime import date

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.engine import Base


class DailyActivity(Base):
    __tablename__ = "daily_activity"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    language_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    pages_read: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("1")
    )

    __table_args__ = (
        sa.UniqueConstraint("user_id", "language_id", "date", name="uq_daily_activity"),
    )
