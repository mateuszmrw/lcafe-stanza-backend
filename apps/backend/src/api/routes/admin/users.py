import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.api.schemas.admin import UserAdminCreateRequest, UserAdminResponse, UserAdminUpdateRequest
from src.domain.auth.services.password import hash_password
from src.infrastructure.db.models.users import User

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("", response_model=list[UserAdminResponse])
async def list_users(
    page: int = 1,
    limit: int = 50,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[UserAdminResponse]:
    offset = (page - 1) * limit
    result = await session.execute(
        sa.select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = list(result.scalars().all())
    return [UserAdminResponse.model_validate(u) for u in users]


@router.patch("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserAdminUpdateRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    result = await session.execute(sa.select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.proficiency_level is not None:
        user.proficiency_level = body.proficiency_level
    if body.native_language_code is not None:
        user.native_language_code = body.native_language_code

    await session.commit()
    await session.refresh(user)
    return UserAdminResponse.model_validate(user)


@router.post("", response_model=UserAdminResponse, status_code=201)
async def create_user(
    body: UserAdminCreateRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    existing = await session.execute(
        sa.select(User).where(sa.or_(User.email == body.email, User.username == body.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email or username already taken")

    user = User(
        email=body.email,
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
        proficiency_level=body.proficiency_level,
        native_language_code=body.native_language_code,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserAdminResponse.model_validate(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    result = await session.execute(sa.select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(user)
    await session.commit()
