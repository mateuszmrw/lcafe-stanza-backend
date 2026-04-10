import hashlib

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.domain.auth.services.jwt import create_access_token, create_refresh_token
from src.domain.users.models import UserCreate
from src.domain.users.service import UserService
from src.infrastructure.db.models.users import User

router = APIRouter(prefix="/setup", tags=["setup"])
_user_service = UserService()


class SetupStatus(BaseModel):
    needs_setup: bool


class SetupRegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class SetupRegisterResponse(BaseModel):
    access_token: str
    refresh_token: str


async def _admin_exists(session: AsyncSession) -> bool:
    result = await session.scalar(
        sa.select(sa.func.count()).select_from(User).where(User.role == "admin")
    )
    return (result or 0) > 0


@router.get("/status", response_model=SetupStatus)
async def setup_status(session: AsyncSession = Depends(get_db)) -> SetupStatus:
    """Return whether the instance needs first-time admin setup."""
    return SetupStatus(needs_setup=not await _admin_exists(session))


@router.post("/register", response_model=SetupRegisterResponse, status_code=201)
async def setup_register(
    body: SetupRegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> SetupRegisterResponse:
    """Register the first admin user. Rejected once an admin already exists."""
    if await _admin_exists(session):
        raise HTTPException(status_code=409, detail="Setup already completed")

    try:
        user = await _user_service.register(
            session, UserCreate(email=body.email, username=body.username, password=body.password)
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    user.role = "admin"
    await session.flush()

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    await _user_service.set_refresh_token_hash(session, user.id, refresh_hash)
    await session.commit()

    return SetupRegisterResponse(access_token=access_token, refresh_token=refresh_token)
