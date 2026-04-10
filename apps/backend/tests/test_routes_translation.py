import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from src.domain.users.models import UserCreate
from src.infrastructure.db.repositories.user_repo import UserRepository


@pytest.fixture
async def authenticated_user(test_session: AsyncSession, test_client: AsyncClient):
    """Create an authenticated user."""
    repo = UserRepository()
    user_create = UserCreate(
        email="translator@example.com",
        username="translator",
        password="password123",
    )
    user = await repo.create(test_session, user_create)
    await test_session.flush()
    await test_session.commit()

    # Login
    login_response = await test_client.post(
        "/auth/login",
        json={"email": "translator@example.com", "password": "password123"},
    )
    access_token = login_response.json()["access_token"]

    return user, access_token


class TestTranslateEndpoint:
    """Test POST /translate endpoint."""

    @pytest.mark.asyncio
    async def test_translate_with_env_key(
        self,
        test_client: AsyncClient,
        authenticated_user,
        monkeypatch,
    ):
        """Test translation uses env API key when no user key exists."""
        _, access_token = authenticated_user

        # Patch get_settings in translation route (lru_cache means setenv won't work)
        from src.core.config import Settings
        mock_settings = Settings(
            jwt_secret="test-secret-key-for-testing-only-32ch",
            db_encryption_key="test-encryption-key-32chars!!!!!!",
            db_database="slovo_test",
            deepl_api_key="env-api-key-123",
        )
        monkeypatch.setattr("src.api.routes.translation.get_settings", lambda: mock_settings)

        with patch(
            "src.infrastructure.deepl.client.DeepLClient.translate",
            new_callable=AsyncMock,
        ) as mock_translate:
            mock_translate.return_value = "Translated text"

            response = await test_client.post(
                "/translate",
                json={
                    "text": "Hello world",
                    "source_lang": "en",
                    "target_lang": "de",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["translated_text"] == "Translated text"

    @pytest.mark.asyncio
    async def test_translate_no_api_key(
        self,
        test_client: AsyncClient,
        authenticated_user,
        monkeypatch,
    ):
        """Test translation fails when no API key is configured."""
        _, access_token = authenticated_user

        # Ensure no env key
        monkeypatch.delenv("DEEPL_API_KEY", raising=False)

        response = await test_client.post(
            "/translate",
            json={
                "text": "Hello world",
                "source_lang": "en",
                "target_lang": "de",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "no deepl api key" in detail.lower()

    @pytest.mark.asyncio
    async def test_translate_without_authentication(
        self,
        test_client: AsyncClient,
    ):
        """Test translation endpoint requires authentication."""
        response = await test_client.post(
            "/translate",
            json={
                "text": "Hello world",
                "source_lang": "en",
                "target_lang": "de",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_translate_missing_fields(
        self,
        test_client: AsyncClient,
        authenticated_user,
        monkeypatch,
    ):
        """Test translation with missing required fields."""
        _, access_token = authenticated_user

        monkeypatch.setenv("DEEPL_API_KEY", "test-key")

        response = await test_client.post(
            "/translate",
            json={
                "text": "Hello world",
                # Missing source_lang and target_lang
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_translate_with_valid_request(
        self,
        test_client: AsyncClient,
        authenticated_user,
        monkeypatch,
    ):
        """Test successful translation with valid request."""
        _, access_token = authenticated_user

        from src.core.config import Settings
        mock_settings = Settings(
            jwt_secret="test-secret-key-for-testing-only-32ch",
            db_encryption_key="test-encryption-key-32chars!!!!!!",
            db_database="slovo_test",
            deepl_api_key="test-api-key",
        )
        monkeypatch.setattr("src.api.routes.translation.get_settings", lambda: mock_settings)

        with patch(
            "src.infrastructure.deepl.client.DeepLClient.translate",
            new_callable=AsyncMock,
        ) as mock_translate:
            mock_translate.return_value = "Hallo Welt"

            response = await test_client.post(
                "/translate",
                json={
                    "text": "Hello world",
                    "source_lang": "EN",
                    "target_lang": "DE",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 200
        assert response.json()["translated_text"] == "Hallo Welt"
        mock_translate.assert_called_once()
