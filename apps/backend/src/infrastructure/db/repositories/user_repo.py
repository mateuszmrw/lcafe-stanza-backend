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
