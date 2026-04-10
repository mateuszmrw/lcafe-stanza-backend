import uuid
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.core.config import Settings, get_settings
from src.domain.users.models import UserCreate
from src.infrastructure.db.models.languages import Language, LanguageNlpConfig
from src.infrastructure.db.models.providers import Provider
from src.infrastructure.db.models.users import User
from src.main import app as fastapi_app


@pytest.fixture
def override_settings(monkeypatch):
    """Override application settings for testing."""

    def _override(test_db_url: str | None = None, **kwargs):
        settings = Settings(
            jwt_secret="test-secret-key-for-testing-only-32ch",
            db_encryption_key="test-encryption-key-32chars!!!!!!",
            db_database="slovo_test",
            **kwargs,
        )
        monkeypatch.setattr("src.core.config.get_settings", lambda: settings)
        monkeypatch.setattr("src.api.dependencies.get_settings", lambda: settings)
        monkeypatch.setattr(
            "src.domain.auth.services.jwt.get_settings", lambda: settings
        )
        return settings

    return _override


@pytest.fixture
async def test_client(
    test_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide a FastAPI TestClient with dependency overrides."""

    async def override_get_db():
        yield test_session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield client

    fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def test_user_factory(test_session: AsyncSession):
    """Factory to create test users."""

    async def create_user(
        email: str = "test@example.com",
        username: str = "testuser",
        password: str = "password123",
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email,
            username=username,
            password_hash="",  # Set in UserService in real usage
            is_active=is_active,
        )
        test_session.add(user)
        await test_session.flush()
        return user

    return create_user


@pytest.fixture
async def test_language_factory(test_session: AsyncSession):
    """Factory to create test languages with NLP config."""

    async def create_language(
        code: str = "en",
        name: str = "English",
    ) -> tuple[Language, Provider, LanguageNlpConfig]:
        # Create provider
        provider = Provider(
            slug="stanza",
            name="Stanza NLP",
            type="nlp",
        )
        test_session.add(provider)
        await test_session.flush()

        # Create language
        language = Language(
            code=code,
            name=name,
        )
        test_session.add(language)
        await test_session.flush()

        # Create NLP config
        nlp_config = LanguageNlpConfig(
            language_id=language.id,
            provider_id=provider.id,
            config={"stanza_language_name": code.lower()},
        )
        test_session.add(nlp_config)
        await test_session.flush()

        return language, provider, nlp_config

    return create_language
