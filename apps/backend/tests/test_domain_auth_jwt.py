from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt as pyjwt
import pytest

from src.core.config import Settings
from src.domain.auth.services.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


@pytest.fixture
def jwt_settings():
    """Provide test settings with JWT config."""
    return Settings(
        jwt_secret="test-secret-key",
        jwt_algorith="HS256",
        access_token_expire_minutes=60,
        refresh_token_expire_days=31,
        db_encryption_key="test-key",
    )


@pytest.fixture
def patch_get_settings(monkeypatch, jwt_settings):
    """Patch get_settings to return test settings."""

    def _patch():
        monkeypatch.setattr(
            "src.domain.auth.services.jwt.get_settings",
            lambda: jwt_settings,
        )

    return _patch


class TestCreateAccessToken:
    """Test access token creation."""

    def test_create_access_token_contains_subject(self, patch_get_settings, jwt_settings):
        """Test that access token contains the subject."""
        patch_get_settings()
        subject = "user-id-123"
        token = create_access_token(subject)

        payload = pyjwt.decode(
            token, jwt_settings.jwt_secret, algorithms=[jwt_settings.jwt_algorith]
        )
        assert payload["sub"] == subject

    def test_create_access_token_has_type_access(self, patch_get_settings, jwt_settings):
        """Test that access token has type='access'."""
        patch_get_settings()
        token = create_access_token("user-id-123")

        payload = pyjwt.decode(
            token, jwt_settings.jwt_secret, algorithms=[jwt_settings.jwt_algorith]
        )
        assert payload["type"] == "access"

    def test_create_access_token_has_expiration(self, patch_get_settings, jwt_settings):
        """Test that access token has expiration set."""
        patch_get_settings()
        token = create_access_token("user-id-123")

        payload = pyjwt.decode(
            token, jwt_settings.jwt_secret, algorithms=[jwt_settings.jwt_algorith]
        )
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_with_additional_claims(
        self, patch_get_settings, jwt_settings
    ):
        """Test that additional claims are added to token."""
        patch_get_settings()
        additional_claims = {"role": "admin", "email": "user@example.com"}
        token = create_access_token("user-id-123", additional_claims=additional_claims)

        payload = pyjwt.decode(
            token, jwt_settings.jwt_secret, algorithms=[jwt_settings.jwt_algorith]
        )
        assert payload["role"] == "admin"
        assert payload["email"] == "user@example.com"


class TestCreateRefreshToken:
    """Test refresh token creation."""

    def test_create_refresh_token_contains_subject(
        self, patch_get_settings, jwt_settings
    ):
        """Test that refresh token contains the subject."""
        patch_get_settings()
        subject = "user-id-123"
        token = create_refresh_token(subject)

        payload = pyjwt.decode(
            token, jwt_settings.jwt_secret, algorithms=[jwt_settings.jwt_algorith]
        )
        assert payload["sub"] == subject

    def test_create_refresh_token_has_type_refresh(
        self, patch_get_settings, jwt_settings
    ):
        """Test that refresh token has type='refresh'."""
        patch_get_settings()
        token = create_refresh_token("user-id-123")

        payload = pyjwt.decode(
            token, jwt_settings.jwt_secret, algorithms=[jwt_settings.jwt_algorith]
        )
        assert payload["type"] == "refresh"

    def test_create_refresh_token_has_longer_expiration(
        self, patch_get_settings, jwt_settings
    ):
        """Test that refresh token expires later than access token."""
        patch_get_settings()
        access_token = create_access_token("user-id-123")
        refresh_token = create_refresh_token("user-id-123")

        access_payload = pyjwt.decode(
            access_token, jwt_settings.jwt_secret, algorithms=[jwt_settings.jwt_algorith]
        )
        refresh_payload = pyjwt.decode(
            refresh_token, jwt_settings.jwt_secret, algorithms=[jwt_settings.jwt_algorith]
        )
        # Refresh token should expire later (larger exp value)
        assert refresh_payload["exp"] > access_payload["exp"]


class TestDecodeToken:
    """Test token decoding and validation."""

    def test_decode_token_valid(self, patch_get_settings, jwt_settings):
        """Test decoding a valid token."""
        patch_get_settings()
        subject = "user-id-123"
        token = create_access_token(subject)

        payload = decode_token(token)
        assert payload["sub"] == subject
        assert payload["type"] == "access"

    def test_decode_token_expired(self, monkeypatch, jwt_settings):
        """Test that expired token raises ExpiredSignatureError."""
        # Use negative expiry so token is created already-expired
        expired_settings = Settings(
            jwt_secret=jwt_settings.jwt_secret,
            jwt_algorith=jwt_settings.jwt_algorith,
            access_token_expire_minutes=-60,
            db_encryption_key=jwt_settings.db_encryption_key,
        )
        monkeypatch.setattr(
            "src.domain.auth.services.jwt.get_settings",
            lambda: expired_settings,
        )
        token = create_access_token("user-id-123")

        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_token(token)

    def test_decode_token_wrong_secret(self, patch_get_settings, jwt_settings):
        """Test that token signed with wrong secret raises InvalidTokenError."""
        patch_get_settings()
        subject = "user-id-123"
        token = create_access_token(subject)

        # Try to decode with wrong secret
        with pytest.raises(pyjwt.InvalidTokenError):
            pyjwt.decode(
                token, "wrong-secret", algorithms=[jwt_settings.jwt_algorith]
            )

    def test_decode_token_malformed(self, patch_get_settings, jwt_settings):
        """Test that malformed token raises InvalidTokenError."""
        patch_get_settings()
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token("invalid.token.here")

    def test_decode_token_missing_claims(self, patch_get_settings, jwt_settings):
        """Test decoding a token with missing required claims."""
        patch_get_settings()
        # Create token with minimal claims
        token = pyjwt.encode(
            {"type": "access"}, jwt_settings.jwt_secret, algorithm=jwt_settings.jwt_algorith
        )

        payload = decode_token(token)
        assert "type" in payload
        # The 'sub' claim is optional at decode time, validation is at route level
