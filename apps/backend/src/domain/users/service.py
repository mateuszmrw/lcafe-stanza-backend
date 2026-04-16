from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.auth.services.password import hash_password, verify_password
from src.domain.users.models import UserCreate, UserUpdate
from src.infrastructure.db.models.users import User


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class UserService:
    async def register(self, session: AsyncSession, user_create: UserCreate) -> User:
        email = _normalize_email(user_create.email)
        existing = await self.get_by_email(session, email)
        if existing:
            raise ValueError(f"Email already registered: {email}")

        user = User(
            email=email,
            username=user_create.username,
            password_hash=hash_password(user_create.password),
        )
        session.add(user)
        await session.flush()
        return user

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(
            sa.select(User).where(User.email == _normalize_email(email))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, user_id: uuid.UUID) -> User | None:
        result = await session.execute(
            sa.select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, user_id: uuid.UUID, user_update: UserUpdate
    ) -> User:
        user = await self.get_by_id(session, user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        if user_update.username is not None:
            user.username = user_update.username
        if user_update.password is not None:
            user.password_hash = hash_password(user_update.password)

        await session.flush()
        return user

    async def deactivate(self, session: AsyncSession, user_id: uuid.UUID) -> None:
        user = await self.get_by_id(session, user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        user.is_active = False
        await session.flush()

    async def set_refresh_token_hash(
        self, session: AsyncSession, user_id: uuid.UUID, token_hash: str | None
    ) -> None:
        await session.execute(
            sa.update(User)
            .where(User.id == user_id)
            .values(refresh_token_hash=token_hash)
        )
