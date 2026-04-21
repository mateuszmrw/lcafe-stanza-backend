"""Tests for PATCH /users/me/exercises endpoint."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.users.models import UserCreate
from src.infrastructure.db.repositories.user_repo import UserRepository


@pytest.fixture
async def authenticated_user(test_session: AsyncSession, test_client: AsyncClient):
    repo = UserRepository()
    user = await repo.create(
        test_session,
        UserCreate(email="exercises@example.com", username="exerciseuser", password="password123"),
    )
    await test_session.flush()
    await test_session.commit()

    login = await test_client.post(
        "/auth/login",
        json={"email": "exercises@example.com", "password": "password123"},
    )
    return user, login.json()["access_token"]


class TestUpdateExerciseSettings:
    async def test_update_interval(self, test_client: AsyncClient, authenticated_user):
        user, token = authenticated_user
        resp = await test_client.patch(
            "/users/me/exercises",
            json={"exercises_enabled": True, "exercise_interval_pages": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exercises_enabled"] is True
        assert data["exercise_interval_pages"] == 10

    async def test_disable_exercises(self, test_client: AsyncClient, authenticated_user):
        user, token = authenticated_user
        resp = await test_client.patch(
            "/users/me/exercises",
            json={"exercises_enabled": False, "exercise_interval_pages": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["exercises_enabled"] is False

    async def test_re_enable_exercises(self, test_client: AsyncClient, authenticated_user):
        user, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        await test_client.patch(
            "/users/me/exercises",
            json={"exercises_enabled": False, "exercise_interval_pages": 5},
            headers=headers,
        )
        resp = await test_client.patch(
            "/users/me/exercises",
            json={"exercises_enabled": True, "exercise_interval_pages": 7},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exercises_enabled"] is True
        assert data["exercise_interval_pages"] == 7

    async def test_interval_clamped_to_minimum_one(self, test_client: AsyncClient, authenticated_user):
        user, token = authenticated_user
        resp = await test_client.patch(
            "/users/me/exercises",
            json={"exercises_enabled": True, "exercise_interval_pages": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        # ge=1 validation rejects 0
        assert resp.status_code == 422

    async def test_interval_max_100(self, test_client: AsyncClient, authenticated_user):
        user, token = authenticated_user
        resp = await test_client.patch(
            "/users/me/exercises",
            json={"exercises_enabled": True, "exercise_interval_pages": 101},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_requires_auth(self, test_client: AsyncClient):
        resp = await test_client.patch(
            "/users/me/exercises",
            json={"exercises_enabled": True, "exercise_interval_pages": 5},
        )
        assert resp.status_code == 401

    async def test_settings_persist_in_get_me(self, test_client: AsyncClient, authenticated_user):
        user, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        await test_client.patch(
            "/users/me/exercises",
            json={"exercises_enabled": False, "exercise_interval_pages": 15},
            headers=headers,
        )
        resp = await test_client.get("/users/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["exercises_enabled"] is False
        assert data["exercise_interval_pages"] == 15
