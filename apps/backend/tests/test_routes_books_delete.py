"""
Task 11: Test that DELETE /books/{id} removes both the DB entry and the EPUB
file from disk.
"""
import os
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.infrastructure.db.models.content import Book, ContentItem
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.repositories.user_repo import UserRepository
from src.domain.users.models import UserCreate


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
        UserCreate(email="deleter@example.com", username="deleter", password="password123"),
    )
    await test_session.flush()
    await test_session.commit()

    login = await test_client.post(
        "/auth/login",
        json={"email": "deleter@example.com", "password": "password123"},
    )
    return user, login.json()["access_token"]


class TestDeleteBook:
    @pytest.mark.asyncio
    async def test_delete_removes_db_row(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """DELETE /books/{id} removes the ContentItem row."""
        user, access_token = authenticated_user
        lang_id = test_language.id

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=lang_id,
            type="book",
            title="Delete Me",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        book = Book(
            content_item_id=content_item.id,
            file_hash="abc123",
            file_path="books/nonexistent.epub",
        )
        test_session.add(book)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.delete(
            f"/books/{content_item.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 204

        remaining = await test_session.execute(
            select(ContentItem).where(ContentItem.id == content_item.id)
        )
        assert remaining.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_removes_epub_file(
        self,
        tmp_path,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
        monkeypatch,
    ):
        """DELETE /books/{id} deletes the EPUB file from storage."""
        user, access_token = authenticated_user
        lang_id = test_language.id

        # Create a real file in a temp directory
        books_dir = tmp_path / "books"
        books_dir.mkdir()
        epub_file = books_dir / "test.epub"
        epub_file.write_bytes(b"fake epub content")

        rel_path = "books/test.epub"

        # Patch storage_root so the route builds the correct abs path
        settings = get_settings()
        monkeypatch.setattr(settings, "storage_root", str(tmp_path))
        monkeypatch.setattr("src.api.routes.books.get_settings", lambda: settings)

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=lang_id,
            type="book",
            title="File Delete Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        book = Book(
            content_item_id=content_item.id,
            file_hash="deadbeef",
            file_path=rel_path,
        )
        test_session.add(book)
        await test_session.flush()
        await test_session.commit()

        assert epub_file.exists()

        response = await test_client.delete(
            f"/books/{content_item.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 204
        assert not epub_file.exists()

    @pytest.mark.asyncio
    async def test_delete_tolerates_missing_file(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """DELETE /books/{id} succeeds even if the EPUB file is already gone."""
        user, access_token = authenticated_user
        lang_id = test_language.id

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=lang_id,
            type="book",
            title="Missing File Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        book = Book(
            content_item_id=content_item.id,
            file_hash="missing123",
            file_path="books/does_not_exist.epub",
        )
        test_session.add(book)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.delete(
            f"/books/{content_item.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_other_users_book_returns_404(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Users cannot delete another user's book."""
        _, access_token = authenticated_user
        lang_id = test_language.id

        repo = UserRepository()
        other_user = await repo.create(
            test_session,
            UserCreate(email="other2@example.com", username="other2", password="password123"),
        )
        await test_session.flush()

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=other_user.id,
            language_id=lang_id,
            type="book",
            title="Other's Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.delete(
            f"/books/{content_item.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 404
