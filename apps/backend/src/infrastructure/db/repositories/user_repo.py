from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.auth.services.password import hash_password
from src.domain.users.models import UserCreate, UserUpdate
from src.infrastructure.db.models.users import User


class UserRepository:
    async def find_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(sa.select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def find_by_email_or_username(
        self, session: AsyncSession, email: str, username: str
    ) -> User | None:
        result = await session.execute(
            sa.select(User).where(sa.or_(User.email == email, User.username == username))
        )
        return result.scalar_one_or_none()

    async def count_admins(self, session: AsyncSession) -> int:
        result = await session.scalar(
            sa.select(sa.func.count())
            .select_from(User)
            .where(User.role == "admin")
        )
        return result or 0

    async def find_by_id(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> User | None:
        result = await session.execute(sa.select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, user_create: UserCreate) -> User:
        user = User(
            email=user_create.email,
            username=user_create.username,
            password_hash=hash_password(user_create.password),
        )
        session.add(user)
        await session.flush()
        return user

    async def update(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        user_update: UserUpdate,
    ) -> User | None:
        user = await self.find_by_id(session, user_id)
        if not user:
            return None
        if user_update.username is not None:
            user.username = user_update.username
        if user_update.password is not None:
            user.password_hash = hash_password(user_update.password)
        await session.flush()
        return user

    async def list_all(
        self,
        session: AsyncSession,
        page: int = 1,
        limit: int = 50,
    ) -> list[User]:
        """Return a paginated list of all users, newest first."""
        offset = (page - 1) * limit
        result = await session.execute(
            sa.select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def set_refresh_token_hash(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        token_hash: str | None,
    ) -> None:
        await session.execute(
            sa.update(User)
            .where(User.id == user_id)
            .values(refresh_token_hash=token_hash)
        )

    async def update_exercise_interval(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        interval_pages: int,
    ) -> None:
        """Update exercise_interval_pages for a user, clamping to min 1."""
        clamped = max(1, interval_pages)
        await session.execute(
            sa.update(User)
            .where(User.id == user_id)
            .values(exercise_interval_pages=clamped)
        )

    async def update_exercise_settings(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        enabled: bool,
        interval_pages: int,
    ) -> None:
        """Update exercises_enabled and exercise_interval_pages together."""
        await session.execute(
            sa.update(User)
            .where(User.id == user_id)
            .values(
                exercises_enabled=enabled,
                exercise_interval_pages=max(1, interval_pages),
            )
        )
