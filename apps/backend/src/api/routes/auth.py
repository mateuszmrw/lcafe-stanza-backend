import hashlib
import uuid

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from src.domain.auth.services.jwt import create_access_token, create_refresh_token, decode_token
from src.domain.auth.services.password import verify_password
from src.domain.users.models import UserCreate
from src.domain.users.service import UserService
from src.infrastructure.db.models.users import User

router = APIRouter(prefix="/auth", tags=["auth"])
_user_service = UserService()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        user = await _user_service.register(session, UserCreate(**body.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    await _user_service.set_refresh_token_hash(session, user.id, refresh_hash)
    await session.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await _user_service.get_by_email(session, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account deactivated")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    await _user_service.set_refresh_token_hash(session, user.id, refresh_hash)
    await session.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = uuid.UUID(payload["sub"])
    user = await _user_service.get_by_id(session, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    if user.refresh_token_hash != token_hash:
        raise HTTPException(status_code=401, detail="Refresh token mismatch")

    access_token = create_access_token(str(user.id))
    new_refresh = create_refresh_token(str(user.id))

    new_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
    await _user_service.set_refresh_token_hash(session, user.id, new_hash)
    await session.commit()

    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout", status_code=204)
async def logout(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    await _user_service.set_refresh_token_hash(session, current_user.id, None)
    await session.commit()
