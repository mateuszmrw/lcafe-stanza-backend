"""Tests for the tokenize_page arq worker task."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.users.models import UserCreate
from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.languages import Language, LanguageNlpConfig
from src.infrastructure.db.models.providers import Provider
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.user_repo import UserRepository
from src.worker.tasks.tokenize_page import tokenize_page


@pytest.fixture
def worker_session_factory(test_db_engine):
    return async_sessionmaker(test_db_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def setup(test_session: AsyncSession):
    repo = UserRepository()
    user = await repo.create(
        test_session,
        UserCreate(email="worker@example.com", username="worker", password="pass123"),
    )
    await test_session.flush()

    provider = Provider(slug="stanza", name="Stanza NLP", type="nlp")
    test_session.add(provider)
    await test_session.flush()

    language = Language(code="en", name="English")
    test_session.add(language)
    await test_session.flush()

    nlp_config = LanguageNlpConfig(
        language_id=language.id,
        provider_id=provider.id,
        config={"stanza_language_name": "english"},
    )
    test_session.add(nlp_config)
    await test_session.flush()

    content_item = ContentItem(
        user_id=user.id,
        language_id=language.id,
        type="book",
        title="Worker Test Book",
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

    return user, content_item, page, language


class TestTokenizePage:

    @pytest.mark.asyncio
    async def test_sets_page_status_to_ready(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """tokenize_page marks the page as ready after tokenization."""
        user, content_item, page, _ = setup

        mock_stanza = MagicMock()
        mock_stanza.tokenize_sync.return_value = [
            {"w": "Hello", "l": "hello", "pos": "INTJ", "r": "", "si": 0, "g": ""},
            {"w": "world", "l": "world", "pos": "NOUN", "r": "", "si": 0, "g": ""},
        ]
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=1)
        redis.incrby = AsyncMock(return_value=2)
        redis.expire = AsyncMock()
        redis.get = AsyncMock(return_value=b"1")  # total_pages = 1, so this triggers finalize
        redis.setnx = AsyncMock(return_value=False)  # don't finalize in this test

        ctx = {"redis": redis, "stanza_client": mock_stanza}

        with patch("src.worker.tasks.tokenize_page.AsyncSessionFactory", worker_session_factory), \
             patch("src.worker.tasks.tokenize_page.publish_import_event", new_callable=AsyncMock):
            await tokenize_page(ctx, str(page.id))

        await test_session.refresh(page)
        assert page.status == "ready"

    @pytest.mark.asyncio
    async def test_upserts_words_to_vocabulary(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """tokenize_page writes unique words to the Word table."""
        user, content_item, page, language = setup

        mock_stanza = MagicMock()
        mock_stanza.tokenize_sync.return_value = [
            {"w": "Python", "l": "python", "pos": "NOUN", "r": "", "si": 0, "g": "Neut"},
            {"w": "python", "l": "python", "pos": "NOUN", "r": "", "si": 0, "g": "Neut"},  # duplicate
            {"w": "Code", "l": "code", "pos": "NOUN", "r": "", "si": 0, "g": ""},
        ]
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=1)
        redis.incrby = AsyncMock(return_value=3)
        redis.expire = AsyncMock()
        redis.get = AsyncMock(return_value=b"999")  # not last page
        redis.setnx = AsyncMock(return_value=False)

        ctx = {"redis": redis, "stanza_client": mock_stanza}

        with patch("src.worker.tasks.tokenize_page.AsyncSessionFactory", worker_session_factory), \
             patch("src.worker.tasks.tokenize_page.publish_import_event", new_callable=AsyncMock):
            await tokenize_page(ctx, str(page.id))

        result = await test_session.execute(
            sa.select(Word).where(Word.user_id == user.id, Word.language_id == language.id)
        )
        words = {w.word: w for w in result.scalars().all()}
        assert "python" in words
        assert "code" in words
        assert len(words) == 2
        assert words["python"].gender == "Neut"

    @pytest.mark.asyncio
    async def test_finalizes_when_last_page(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """When the last page completes, the book status becomes completed."""
        user, content_item, page, _ = setup

        mock_stanza = MagicMock()
        mock_stanza.tokenize_sync.return_value = [
            {"w": "Hello", "l": "hello", "pos": "INTJ", "r": "", "si": 0, "g": ""},
        ]
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=1)
        redis.incrby = AsyncMock(return_value=1)
        redis.expire = AsyncMock()
        redis.get = AsyncMock(return_value=b"1")  # total = 1, completed = 1 → last page
        redis.setnx = AsyncMock(return_value=True)  # claim finalization
        redis.delete = AsyncMock()

        ctx = {"redis": redis, "stanza_client": mock_stanza}

        with patch("src.worker.tasks.tokenize_page.AsyncSessionFactory", worker_session_factory), \
             patch("src.worker.tasks.tokenize_page.publish_import_event", new_callable=AsyncMock) as mock_publish:
            await tokenize_page(ctx, str(page.id))

        await test_session.refresh(content_item)
        assert content_item.status == "completed"

        event_types = [call.args[2] for call in mock_publish.call_args_list]
        assert "completed" in event_types

    @pytest.mark.asyncio
    async def test_missing_page_is_skipped(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """tokenize_page returns without error for a nonexistent page ID."""
        redis = AsyncMock()
        mock_stanza = MagicMock()
        ctx = {"redis": redis, "stanza_client": mock_stanza}

        with patch("src.worker.tasks.tokenize_page.AsyncSessionFactory", worker_session_factory), \
             patch("src.worker.tasks.tokenize_page.publish_import_event", new_callable=AsyncMock):
            # Should not raise
            await tokenize_page(ctx, str(uuid.uuid4()))
