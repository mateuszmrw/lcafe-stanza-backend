"""
Tests for:
  - GET /books/{id}/chapters  (chapter summary list)
  - GET /books/{id}/pages?chapter=N  (chapter filter)
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.users.models import UserCreate
from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.languages import Language
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
    user = await repo.create(
        test_session,
        UserCreate(email="chapters@example.com", username="chapters", password="password123"),
    )
    await test_session.flush()
    await test_session.commit()

    login = await test_client.post(
        "/auth/login",
        json={"email": "chapters@example.com", "password": "password123"},
    )
    return user, login.json()["access_token"]


async def _book_with_chapters(
    test_session: AsyncSession,
    user_id: uuid.UUID,
    lang_id: int,
) -> ContentItem:
    """Create a book with 3 chapters, 2 pages each."""
    content_item = ContentItem(
        id=uuid.uuid4(),
        user_id=user_id,
        language_id=lang_id,
        type="book",
        title="Chapter Test Book",
        status="completed",
    )
    test_session.add(content_item)
    await test_session.flush()

    pages = [
        ContentPage(
            content_item_id=content_item.id,
            page_number=i,
            chapter_number=(i - 1) // 2 + 1,
            chapter_name=f"Chapter {(i - 1) // 2 + 1}",
            text=f"Text for page {i}",
            status="ready",
        )
        for i in range(1, 7)
    ]
    test_session.add_all(pages)
    await test_session.flush()
    await test_session.commit()
    return content_item


class TestGetChapters:
    @pytest.mark.asyncio
    async def test_returns_chapter_list(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """GET /books/{id}/chapters returns one entry per chapter."""
        user, access_token = authenticated_user
        book = await _book_with_chapters(test_session, user.id, test_language.id)

        response = await test_client.get(
            f"/books/{book.id}/chapters",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        chapters = response.json()
        assert len(chapters) == 3

    @pytest.mark.asyncio
    async def test_chapter_fields(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Each chapter entry has the expected shape."""
        user, access_token = authenticated_user
        book = await _book_with_chapters(test_session, user.id, test_language.id)

        response = await test_client.get(
            f"/books/{book.id}/chapters",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        chapters = response.json()
        ch1 = chapters[0]
        assert ch1["chapter_number"] == 1
        assert ch1["chapter_name"] == "Chapter 1"
        assert ch1["first_page_number"] == 1
        assert ch1["page_count"] == 2

    @pytest.mark.asyncio
    async def test_chapters_ordered_by_number(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Chapters are returned in ascending chapter_number order."""
        user, access_token = authenticated_user
        book = await _book_with_chapters(test_session, user.id, test_language.id)

        response = await test_client.get(
            f"/books/{book.id}/chapters",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        chapters = response.json()
        numbers = [c["chapter_number"] for c in chapters]
        assert numbers == sorted(numbers)

    @pytest.mark.asyncio
    async def test_chapters_empty_book(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """A book with no pages returns an empty chapter list."""
        user, access_token = authenticated_user

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=test_language.id,
            type="book",
            title="Empty Book",
            status="processing",
        )
        test_session.add(content_item)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.get(
            f"/books/{content_item.id}/chapters",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_chapters_404_for_other_users_book(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Requesting chapters for another user's book returns 404."""
        _, access_token = authenticated_user

        repo = UserRepository()
        other_user = await repo.create(
            test_session,
            UserCreate(email="otherch@example.com", username="otherch", password="password123"),
        )
        await test_session.flush()

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=other_user.id,
            language_id=test_language.id,
            type="book",
            title="Other's Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.get(
            f"/books/{content_item.id}/chapters",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chapters_requires_auth(self, test_client: AsyncClient):
        response = await test_client.get(f"/books/{uuid.uuid4()}/chapters")
        assert response.status_code == 401


class TestChapterFilter:
    @pytest.mark.asyncio
    async def test_chapter_filter_returns_only_that_chapter(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """?chapter=N returns only pages belonging to that chapter."""
        user, access_token = authenticated_user
        book = await _book_with_chapters(test_session, user.id, test_language.id)

        response = await test_client.get(
            f"/books/{book.id}/pages?chapter=2",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for page in data["items"]:
            assert page["chapter_number"] == 2

    @pytest.mark.asyncio
    async def test_chapter_filter_nonexistent_chapter_returns_empty(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """?chapter=99 for a book with 3 chapters returns total=0."""
        user, access_token = authenticated_user
        book = await _book_with_chapters(test_session, user.id, test_language.id)

        response = await test_client.get(
            f"/books/{book.id}/pages?chapter=99",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_no_chapter_filter_returns_all_pages(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Without ?chapter= the endpoint returns all pages (existing behaviour)."""
        user, access_token = authenticated_user
        book = await _book_with_chapters(test_session, user.id, test_language.id)

        response = await test_client.get(
            f"/books/{book.id}/pages?limit=10",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 6  # 3 chapters × 2 pages

    @pytest.mark.asyncio
    async def test_chapter_filter_combined_with_pagination(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """?chapter=N works correctly with page/limit pagination."""
        user, access_token = authenticated_user

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=test_language.id,
            type="book",
            title="Paginated Chapter Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        pages = [
            ContentPage(
                content_item_id=content_item.id,
                page_number=i,
                chapter_number=1,
                chapter_name="Chapter 1",
                text=f"Page {i} text",
                status="ready",
            )
            for i in range(1, 5)  # 4 pages in chapter 1
        ]
        test_session.add_all(pages)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.get(
            f"/books/{content_item.id}/pages?chapter=1&page=1&limit=2",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert len(data["items"]) == 2
