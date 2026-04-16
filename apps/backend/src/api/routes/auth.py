import hashlib
import uuid

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.api.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from src.domain.auth.services.jwt import create_access_token, create_refresh_token, decode_token
from src.domain.auth.services.password import hash_password, verify_password
from src.domain.rate_limit import check_rate_limit
from src.domain.users.models import UserCreate
from src.domain.users.service import UserService
from src.infrastructure.db.models.users import User

router = APIRouter(prefix="/auth", tags=["auth"])
_user_service = UserService()

# Pre-computed bcrypt hash for constant-time login — prevents email enumeration
# via timing. verify_password always runs even when the user doesn't exist.
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-not-used-for-auth")


def _client_ip(request: Request) -> str:
    """Best-effort client IP for rate limiting (X-Forwarded-For aware)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    # 5 registrations per hour per IP — prevents spam + enumeration.
    await check_rate_limit(redis, f"auth:register:{_client_ip(request)}", limit=5, window_seconds=3600)

    # Normalize email so different casings resolve to the same account.
    user_data = body.model_dump()
    user_data["email"] = _normalize_email(user_data["email"])

    try:
        user = await _user_service.register(session, UserCreate(**user_data))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    access_token = create_access_token(str(user.id), additional_claims={"ver": user.token_version})
    refresh_token = create_refresh_token(str(user.id))

    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    await _user_service.set_refresh_token_hash(session, user.id, refresh_hash)
    await session.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    # Rate limit per IP (5/min) and per email (10/hour) to slow brute force.
    client_ip = _client_ip(request)
    email = _normalize_email(body.email)
    await check_rate_limit(redis, f"auth:login:ip:{client_ip}", limit=5, window_seconds=60)
    await check_rate_limit(redis, f"auth:login:email:{email}", limit=10, window_seconds=3600)

    user = await _user_service.get_by_email(session, email)

    # Always hash-compare (even when user is missing) so response time is constant.
    # Otherwise an attacker can enumerate valid emails by measuring the delay.
    password_valid = verify_password(
        body.password,
        user.password_hash if user else _DUMMY_PASSWORD_HASH,
    )

    if not user or not password_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account deactivated")

    # Bump the token version to invalidate all existing sessions on other devices
    user.token_version = (user.token_version or 0) + 1
    await session.flush()

    access_token = create_access_token(str(user.id), additional_claims={"ver": user.token_version})
    refresh_token = create_refresh_token(str(user.id))

    refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    await _user_service.set_refresh_token_hash(session, user.id, refresh_hash)
    await session.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    # Limit refresh attempts to slow down stolen-token abuse.
    await check_rate_limit(redis, f"auth:refresh:{_client_ip(request)}", limit=20, window_seconds=60)

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
        # Refresh token reuse — either the legitimate user re-logged-in (which
        # bumped the hash), or a stolen token is being replayed. Revoke all
        # sessions by clearing the refresh hash + bumping token_version.
        user.refresh_token_hash = None
        user.token_version = (user.token_version or 0) + 1
        await session.commit()
        raise HTTPException(status_code=401, detail="Refresh token mismatch — session revoked")

    access_token = create_access_token(str(user.id), additional_claims={"ver": user.token_version})
    new_refresh = create_refresh_token(str(user.id))

    new_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
    await _user_service.set_refresh_token_hash(session, user.id, new_hash)
    await session.commit()

    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout", status_code=204)
async def logout(
    all_devices: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Log out the current session. Pass ?all_devices=true to invalidate every
    active session (useful if the user suspects credential compromise).
    """
    await _user_service.set_refresh_token_hash(session, current_user.id, None)
    if all_devices:
        # Bump token_version so existing access tokens on other devices fail
        # the `ver` check in get_current_user.
        current_user.token_version = (current_user.token_version or 0) + 1
    await session.commit()
