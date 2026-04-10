import hashlib
import json
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.auth import _user_service
from src.domain.auth.services.password import hash_password, verify_password
from src.domain.users.models import UserCreate
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.user_repo import UserRepository


@pytest.fixture
async def test_user(test_session: AsyncSession):
    """Create a test user in the database."""
    repo = UserRepository()
    user_create = UserCreate(
        email="testuser@example.com",
        username="testuser",
        password="password123",
    )
    user = await repo.create(test_session, user_create)
    await test_session.flush()
    await test_session.commit()
    return user


class TestRegisterEndpoint:
    """Test POST /auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, test_client: AsyncClient, test_session):
        """Test successful user registration."""
        payload = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepass123",
        }

        response = await test_client.post("/auth/register", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, test_client: AsyncClient, test_user: User
    ):
        """Test registration with duplicate email."""
        payload = {
            "email": test_user.email,
            "username": "differentuser",
            "password": "password123",
        }

        response = await test_client.post("/auth/register", json=payload)

        assert response.status_code == 409
        data = response.json()
        assert "already registered" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, test_client: AsyncClient):
        """Test registration with invalid email format."""
        payload = {
            "email": "not-an-email",
            "username": "someuser",
            "password": "password123",
        }

        response = await test_client.post("/auth/register", json=payload)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, test_client: AsyncClient):
        """Test registration with missing required fields."""
        payload = {
            "email": "user@example.com",
            "username": "user",
            # Missing password
        }

        response = await test_client.post("/auth/register", json=payload)

        assert response.status_code == 422


class TestLoginEndpoint:
    """Test POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, test_client: AsyncClient, test_user: User):
        """Test successful login."""
        payload = {
            "email": test_user.email,
            "password": "password123",
        }

        response = await test_client.post("/auth/login", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client: AsyncClient, test_user: User):
        """Test login with wrong password."""
        payload = {
            "email": test_user.email,
            "password": "wrongpassword",
        }

        response = await test_client.post("/auth/login", json=payload)

        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, test_client: AsyncClient):
        """Test login with non-existent email."""
        payload = {
            "email": "nonexistent@example.com",
            "password": "password123",
        }

        response = await test_client.post("/auth/login", json=payload)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self, test_session: AsyncSession, test_client: AsyncClient
    ):
        """Test login with inactive user."""
        repo = UserRepository()
        user_create = UserCreate(
            email="inactive@example.com",
            username="inactive",
            password="password123",
        )
        user = await repo.create(test_session, user_create)
        user.is_active = False
        await test_session.flush()
        await test_session.commit()

        payload = {
            "email": "inactive@example.com",
            "password": "password123",
        }

        response = await test_client.post("/auth/login", json=payload)

        assert response.status_code == 401
        assert "deactivated" in response.json()["detail"].lower()


class TestRefreshEndpoint:
    """Test POST /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(
        self, test_client: AsyncClient, test_user: User, test_session: AsyncSession
    ):
        """Test successful token refresh."""
        # First, login to get tokens
        login_response = await test_client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Now refresh
        response = await test_client.post(
            "/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_expired_token(self, test_client: AsyncClient):
        """Test refresh with expired refresh token."""
        # Create an expired token
        from datetime import UTC, datetime, timedelta

        from src.core.config import get_settings

        settings = get_settings()
        now = datetime.now(UTC)
        expired_payload = {
            "sub": "some-user-id",
            "iat": now - timedelta(days=32),
            "exp": now - timedelta(days=1),
            "type": "refresh",
        }
        expired_token = pyjwt.encode(
            expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorith
        )

        response = await test_client.post(
            "/auth/refresh", json={"refresh_token": expired_token}
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, test_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await test_client.post(
            "/auth/refresh", json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_access_token_instead_of_refresh(
        self, test_client: AsyncClient, test_user: User
    ):
        """Test refresh endpoint with access token (wrong type)."""
        # Login to get access token
        login_response = await test_client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Try to use access token as refresh token
        response = await test_client.post(
            "/auth/refresh", json={"refresh_token": access_token}
        )

        assert response.status_code == 401
        assert "not a refresh token" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_with_mismatched_hash(
        self, test_client: AsyncClient, test_user: User, test_session: AsyncSession
    ):
        """Test refresh with token hash mismatch."""
        # Login normally
        login_response = await test_client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Manually change the stored hash to cause mismatch
        repo = UserRepository()
        await repo.set_refresh_token_hash(
            test_session, test_user.id, "wronghash123"
        )
        await test_session.commit()

        # Try to refresh
        response = await test_client.post(
            "/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert response.status_code == 401
        assert "mismatch" in response.json()["detail"].lower()


class TestLogoutEndpoint:
    """Test POST /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(
        self, test_client: AsyncClient, test_user: User, test_session: AsyncSession
    ):
        """Test successful logout."""
        # Login first
        login_response = await test_client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # Logout with access token
        response = await test_client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 204

        # Verify refresh token hash was cleared
        repo = UserRepository()
        user = await repo.find_by_id(test_session, test_user.id)
        assert user.refresh_token_hash is None

    @pytest.mark.asyncio
    async def test_logout_without_auth(self, test_client: AsyncClient):
        """Test logout without authentication."""
        response = await test_client.post("/auth/logout")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_with_invalid_token(self, test_client: AsyncClient):
        """Test logout with invalid token."""
        response = await test_client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401
