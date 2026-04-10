from datetime import UTC, datetime, timedelta

import jwt

from src.core.config import get_settings


def create_access_token(subject: str, additional_claims: dict | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
    }
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorith)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorith)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure."""
    settings = get_settings()
    return jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorith]
    )
