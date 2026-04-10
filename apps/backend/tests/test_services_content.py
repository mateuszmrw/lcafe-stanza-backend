import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.content.service import ContentService
from src.infrastructure.db.models.content import Book, ContentItem
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.users import User


@pytest.fixture
def content_service():
    """Provide a ContentService instance."""
    return ContentService()


@pytest.fixture
async def test_user_id(test_session: AsyncSession) -> uuid.UUID:
    """Create a real user in the DB and return its ID."""
    user = User(
        email=f"contenttest-{uuid.uuid4().hex[:8]}@example.com",
        username=f"contentuser-{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
    )
    test_session.add(user)
    await test_session.flush()
    return user.id


@pytest.fixture
async def test_language_id(test_session: AsyncSession) -> int:
    """Create a real language in the DB and return its ID."""
    lang = Language(code=f"cl{uuid.uuid4().hex[:4]}", name="ContentLang")
    test_session.add(lang)
    await test_session.flush()
    return lang.id


class TestCheckDuplicateHash:
    """Test ContentService.check_duplicate_hash()."""

    @pytest.mark.asyncio
    async def test_check_duplicate_no_prior_book(
        self,
        test_session: AsyncSession,
        content_service: ContentService,
        test_user_id: uuid.UUID,
    ):
        """Test duplicate check returns None when no prior book exists."""
        result = await content_service.check_duplicate_hash(
            test_session, test_user_id, "nonexistent-hash"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_check_duplicate_completed_book(
        self,
        test_session: AsyncSession,
        content_service: ContentService,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test duplicate check returns 'completed' status."""
        file_hash = "completed-book-hash"

        content_item = ContentItem(
            user_id=test_user_id,
            language_id=test_language_id,
            type="book",
            title="Completed Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        book = Book(
            content_item_id=content_item.id,
            file_hash=file_hash,
            file_path="/path/to/book.epub",
        )
        test_session.add(book)
        await test_session.flush()

        result = await content_service.check_duplicate_hash(
            test_session, test_user_id, file_hash
        )

        assert result == "completed"

    @pytest.mark.asyncio
    async def test_check_duplicate_processing_book(
        self,
        test_session: AsyncSession,
        content_service: ContentService,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test duplicate check returns 'processing' status."""
        file_hash = "processing-book-hash"

        content_item = ContentItem(
            user_id=test_user_id,
            language_id=test_language_id,
            type="book",
            title="Processing Book",
            status="processing",
        )
        test_session.add(content_item)
        await test_session.flush()

        book = Book(
            content_item_id=content_item.id,
            file_hash=file_hash,
            file_path="/path/to/book.epub",
        )
        test_session.add(book)
        await test_session.flush()

        result = await content_service.check_duplicate_hash(
            test_session, test_user_id, file_hash
        )

        assert result == "processing"

    @pytest.mark.asyncio
    async def test_check_duplicate_pending_book(
        self,
        test_session: AsyncSession,
        content_service: ContentService,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test duplicate check returns 'pending' status."""
        file_hash = "pending-book-hash"

        content_item = ContentItem(
            user_id=test_user_id,
            language_id=test_language_id,
            type="book",
            title="Pending Book",
            status="pending",
        )
        test_session.add(content_item)
        await test_session.flush()

        book = Book(
            content_item_id=content_item.id,
            file_hash=file_hash,
            file_path="/path/to/book.epub",
        )
        test_session.add(book)
        await test_session.flush()

        result = await content_service.check_duplicate_hash(
            test_session, test_user_id, file_hash
        )

        assert result == "pending"

    @pytest.mark.asyncio
    async def test_check_duplicate_failed_book(
        self,
        test_session: AsyncSession,
        content_service: ContentService,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test duplicate check returns 'failed' status (allows re-upload)."""
        file_hash = "failed-book-hash"

        content_item = ContentItem(
            user_id=test_user_id,
            language_id=test_language_id,
            type="book",
            title="Failed Book",
            status="failed",
            error_message="Import error",
        )
        test_session.add(content_item)
        await test_session.flush()

        book = Book(
            content_item_id=content_item.id,
            file_hash=file_hash,
            file_path="/path/to/book.epub",
        )
        test_session.add(book)
        await test_session.flush()

        result = await content_service.check_duplicate_hash(
            test_session, test_user_id, file_hash
        )

        assert result == "failed"

    @pytest.mark.asyncio
    async def test_check_duplicate_different_user(
        self,
        test_session: AsyncSession,
        content_service: ContentService,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test that duplicate check is user-specific."""
        file_hash = "shared-hash"

        # Create a real other user
        other_user = User(
            email=f"other-{uuid.uuid4().hex[:8]}@example.com",
            username=f"otheruser-{uuid.uuid4().hex[:8]}",
            password_hash="hashed",
        )
        test_session.add(other_user)
        await test_session.flush()

        # Create book for other user
        content_item = ContentItem(
            user_id=other_user.id,
            language_id=test_language_id,
            type="book",
            title="Other User's Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        book = Book(
            content_item_id=content_item.id,
            file_hash=file_hash,
            file_path="/path/to/book.epub",
        )
        test_session.add(book)
        await test_session.flush()

        # Check for test user should return None (different user)
        result = await content_service.check_duplicate_hash(
            test_session, test_user_id, file_hash
        )

        assert result is None
