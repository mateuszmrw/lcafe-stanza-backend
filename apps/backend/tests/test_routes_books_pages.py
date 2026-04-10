import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.users.models import UserCreate
from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.user_repo import UserRepository


@pytest.fixture
async def test_language(test_session: AsyncSession) -> Language:
    lang = Language(code="en", name="English")
    test_session.add(lang)
    await test_session.flush()
    await test_session.commit()
    return lang


@pytest.fixture
async def authenticated_user(test_session: AsyncSession, test_client: AsyncClient):
    repo = UserRepository()
    user_create = UserCreate(
        email="reader@example.com",
        username="reader",
        password="password123",
    )
    user = await repo.create(test_session, user_create)
    await test_session.flush()
    await test_session.commit()

    login_response = await test_client.post(
        "/auth/login",
        json={"email": "reader@example.com", "password": "password123"},
    )
    access_token = login_response.json()["access_token"]

    return user, access_token


class TestGetBookPages:
    """Test GET /books/{book_id}/pages endpoint."""

    @pytest.mark.asyncio
    async def test_get_pages_with_vocabulary_enrichment(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Pages with status=ready return tokens enriched from the Word table."""
        user, access_token = authenticated_user
        lang_id = test_language.id

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=lang_id,
            type="book",
            title="Test Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        page1 = ContentPage(
            content_item_id=content_item.id,
            page_number=1,
            text="Hello world Python",
            status="ready",
        )
        test_session.add(page1)
        await test_session.flush()

        word_hello = Word(
            user_id=user.id, language_id=lang_id, word="hello",
            lemma="hello", pos="INTJ", reading="", gender="", status="learning",
        )
        word_world = Word(
            user_id=user.id, language_id=lang_id, word="world",
            lemma="world", pos="NOUN", reading="", gender="", status="known",
        )
        test_session.add_all([word_hello, word_world])
        await test_session.flush()
        await test_session.commit()

        response = await test_client.get(
            f"/books/{content_item.id}/pages",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        page = data["items"][0]

        assert page["status"] == "ready"
        token_map = {t["w"].lower(): t for t in page["tokens"]}
        assert token_map["hello"]["status"] == "learning"
        assert token_map["hello"]["pos"] == "INTJ"
        assert token_map["world"]["status"] == "known"
        assert token_map["python"]["status"] == "new"

    @pytest.mark.asyncio
    async def test_get_pages_pending_returns_empty_tokens(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Pages with status=pending return empty tokens list."""
        user, access_token = authenticated_user
        lang_id = test_language.id

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=lang_id,
            type="book",
            title="Pending Book",
            status="processing",
        )
        test_session.add(content_item)
        await test_session.flush()

        page = ContentPage(
            content_item_id=content_item.id,
            page_number=1,
            text="Hello world",
            status="pending",
        )
        test_session.add(page)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.get(
            f"/books/{content_item.id}/pages",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        page_data = data["items"][0]
        assert page_data["status"] == "pending"
        assert page_data["tokens"] == []

    @pytest.mark.asyncio
    async def test_get_pages_multiple_pages_pagination(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Pagination works correctly across multiple pages."""
        user, access_token = authenticated_user
        lang_id = test_language.id

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=lang_id,
            type="book",
            title="Multi-page Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        for i in range(5):
            page = ContentPage(
                content_item_id=content_item.id,
                page_number=i + 1,
                text=f"Page {i + 1} content",
                status="ready",
            )
            test_session.add(page)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.get(
            f"/books/{content_item.id}/pages?page=1&limit=2",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["limit"] == 2

    @pytest.mark.asyncio
    async def test_get_pages_unauthorized_user(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Users cannot see other users' books."""
        _, access_token = authenticated_user
        lang_id = test_language.id

        repo = UserRepository()
        other_user = await repo.create(
            test_session,
            UserCreate(email="other@example.com", username="other", password="password123"),
        )
        await test_session.flush()

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=other_user.id,
            language_id=lang_id,
            type="book",
            title="Other User's Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.get(
            f"/books/{content_item.id}/pages",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_pages_nonexistent_book(
        self,
        test_client: AsyncClient,
        authenticated_user,
    ):
        _, access_token = authenticated_user
        response = await test_client.get(
            f"/books/{uuid.uuid4()}/pages",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_pages_without_authentication(
        self,
        test_client: AsyncClient,
    ):
        response = await test_client.get(f"/books/{uuid.uuid4()}/pages")
        assert response.status_code == 401
