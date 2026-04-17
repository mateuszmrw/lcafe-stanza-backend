import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.api.schemas.admin import UserAdminCreateRequest, UserAdminResponse, UserAdminUpdateRequest
from src.domain.auth.services.password import hash_password
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.user_repo import UserRepository

router = APIRouter(prefix="/admin/users", tags=["admin"])
_user_repo = UserRepository()


@router.get("", response_model=list[UserAdminResponse])
async def list_users(
    page: int = 1,
    limit: int = 50,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[UserAdminResponse]:
    users = await _user_repo.list_all(session, page=page, limit=limit)
    return [UserAdminResponse.model_validate(u) for u in users]


@router.patch("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserAdminUpdateRequest,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    user = await _user_repo.find_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    editing_self = user_id == current_admin.id
    if editing_self and body.role is not None and body.role != current_admin.role:
        raise HTTPException(
            status_code=400,
            detail="Cannot change your own role. Ask another admin.",
        )
    if editing_self and body.is_active is False:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate your own account.",
        )
    if (
        user.role == "admin"
        and body.role is not None
        and body.role != "admin"
    ):
        admin_count = await _user_repo.count_admins(session)
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot demote the last admin. Promote another user first.",
            )

    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)
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
    existing = await _user_repo.find_by_email_or_username(
        session, body.email, body.username
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email or username already taken")

    user = User(
        email=body.email,
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
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
    user = await _user_repo.find_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting the last admin — instance would become unrecoverable.
    if user.role == "admin":
        admin_count = await _user_repo.count_admins(session)
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last admin. Promote another user first.",
            )

    await session.delete(user)
    await session.commit()
