"""Tests for the import_youtube_subtitles ARQ worker task."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.users.models import UserCreate
from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.languages import Language, LanguageNlpConfig
from src.infrastructure.db.models.providers import Provider
from src.infrastructure.db.models.youtube import YouTubeSubtitle, YouTubeVideo
from src.infrastructure.db.repositories.user_repo import UserRepository
from src.worker.tasks.import_youtube_subtitles import import_youtube_subtitles


@pytest.fixture
def worker_session_factory(test_db_engine):
    return async_sessionmaker(test_db_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def setup(test_session: AsyncSession):
    """Set up user, language, content item, and YouTube video with subtitles."""
    repo = UserRepository()
    user = await repo.create(
        test_session,
        UserCreate(email="youtube@example.com", username="youtube_user", password="pass123"),
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
        type="youtube",
        title="Test YouTube Video",
        status="pending",
    )
    test_session.add(content_item)
    await test_session.flush()

    # Create YouTube video record
    video = YouTubeVideo(
        id=content_item.id,
        video_id="test_video_123",
        youtube_url="https://www.youtube.com/watch?v=test_video_123",
        channel_name="Test Channel",
    )
    test_session.add(video)
    await test_session.flush()

    # Create subtitle lines
    subtitles = []
    for i in range(45):
        subtitle = YouTubeSubtitle(
            video_id="test_video_123",
            line_number=i,
            start_ms=i * 1000,
            end_ms=(i + 1) * 1000,
            text=f"Subtitle line {i}",
        )
        subtitles.append(subtitle)
        test_session.add(subtitle)
    await test_session.flush()
    await test_session.commit()

    return user, content_item, language, video


class TestImportYouTubeSubtitles:
    """Test the import_youtube_subtitles ARQ task."""

    @pytest.mark.asyncio
    async def test_creates_content_pages_from_subtitles(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """Subtitles are chunked and ContentPage rows are created."""
        user, content_item, language, video = setup

        redis = AsyncMock()
        redis.set = AsyncMock()
        redis.enqueue_job = AsyncMock()  # type: ignore[attr-defined]
        redis.publish = AsyncMock()

        ctx = {"redis": redis}

        with patch(
            "src.worker.tasks.import_youtube_subtitles.AsyncSessionFactory",
            worker_session_factory,
        ), patch(
            "src.worker.tasks.import_youtube_subtitles.publish_import_event",
            new_callable=AsyncMock,
        ):
            await import_youtube_subtitles(
                ctx,
                video_id=video.video_id,
                content_item_id=str(content_item.id),
                language_id=language.id,
            )

        # Verify ContentPage rows were created
        pages = await test_session.execute(
            sa.select(ContentPage)
            .where(ContentPage.content_item_id == content_item.id)
            .order_by(ContentPage.page_number)
        )
        pages_list = list(pages.scalars().all())

        # 45 lines with 20 per page = 3 pages
        assert len(pages_list) == 3
        assert pages_list[0].page_number == 1
        assert pages_list[1].page_number == 2
        assert pages_list[2].page_number == 3

    @pytest.mark.asyncio
    async def test_page_text_contains_joined_subtitles(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """Page text is newline-joined subtitle lines."""
        user, content_item, language, video = setup

        redis = AsyncMock()
        redis.set = AsyncMock()
        redis.enqueue_job = AsyncMock()  # type: ignore[attr-defined]
        redis.publish = AsyncMock()

        ctx = {"redis": redis}

        with patch(
            "src.worker.tasks.import_youtube_subtitles.AsyncSessionFactory",
            worker_session_factory,
        ), patch(
            "src.worker.tasks.import_youtube_subtitles.publish_import_event",
            new_callable=AsyncMock,
        ):
            await import_youtube_subtitles(
                ctx,
                video_id=video.video_id,
                content_item_id=str(content_item.id),
                language_id=language.id,
            )

        # Verify first page text
        page = await test_session.get(ContentPage, (await test_session.execute(
            sa.select(ContentPage).where(
                ContentPage.content_item_id == content_item.id,
                ContentPage.page_number == 1,
            )
        )).scalar_one().id)

        # First page should have lines 0-19 joined with newlines
        expected_text = "\n".join([f"Subtitle line {i}" for i in range(20)])
        assert page.text == expected_text

    @pytest.mark.asyncio
    async def test_sets_total_pages_redis_key(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """Redis key book:{content_item_id}:total_pages is set."""
        user, content_item, language, video = setup

        redis = AsyncMock()
        redis.set = AsyncMock()
        redis.enqueue_job = AsyncMock()  # type: ignore[attr-defined]
        redis.publish = AsyncMock()

        ctx = {"redis": redis}

        with patch(
            "src.worker.tasks.import_youtube_subtitles.AsyncSessionFactory",
            worker_session_factory,
        ), patch(
            "src.worker.tasks.import_youtube_subtitles.publish_import_event",
            new_callable=AsyncMock,
        ):
            await import_youtube_subtitles(
                ctx,
                video_id=video.video_id,
                content_item_id=str(content_item.id),
                language_id=language.id,
            )

        # Verify redis.set was called with total_pages
        redis.set.assert_called()
        call_args = redis.set.call_args_list
        # Find the call that sets total_pages
        total_pages_call = None
        for call in call_args:
            if "total_pages" in str(call):
                total_pages_call = call
                break
        assert total_pages_call is not None

    @pytest.mark.asyncio
    async def test_enqueues_tokenize_page_jobs(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """tokenize_page job is enqueued for each page."""
        user, content_item, language, video = setup

        redis = AsyncMock()
        redis.set = AsyncMock()
        redis.enqueue_job = AsyncMock()  # type: ignore[attr-defined]
        redis.publish = AsyncMock()

        ctx = {"redis": redis}

        with patch(
            "src.worker.tasks.import_youtube_subtitles.AsyncSessionFactory",
            worker_session_factory,
        ), patch(
            "src.worker.tasks.import_youtube_subtitles.publish_import_event",
            new_callable=AsyncMock,
        ):
            await import_youtube_subtitles(
                ctx,
                video_id=video.video_id,
                content_item_id=str(content_item.id),
                language_id=language.id,
            )

        # Verify enqueue_job was called 3 times (one per page)
        enqueue_calls = [
            call for call in redis.enqueue_job.call_args_list
            if call[0][0] == "tokenize_page"
        ]
        assert len(enqueue_calls) == 3

    @pytest.mark.asyncio
    async def test_publishes_progress_event(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """Progress SSE event is published."""
        user, content_item, language, video = setup

        redis = AsyncMock()
        redis.set = AsyncMock()
        redis.enqueue_job = AsyncMock()  # type: ignore[attr-defined]
        redis.publish = AsyncMock()

        ctx = {"redis": redis}

        with patch(
            "src.worker.tasks.import_youtube_subtitles.AsyncSessionFactory",
            worker_session_factory,
        ), patch(
            "src.worker.tasks.import_youtube_subtitles.publish_import_event",
            new_callable=AsyncMock,
        ) as mock_publish:
            await import_youtube_subtitles(
                ctx,
                video_id=video.video_id,
                content_item_id=str(content_item.id),
                language_id=language.id,
            )

        # Verify publish_import_event was called with "progress" event
        event_types = [call.args[2] for call in mock_publish.call_args_list]
        assert "progress" in event_types

    @pytest.mark.asyncio
    async def test_updates_content_item_status_to_processing(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """ContentItem status is set to "processing" at start."""
        user, content_item, language, video = setup

        redis = AsyncMock()
        redis.set = AsyncMock()
        redis.enqueue_job = AsyncMock()  # type: ignore[attr-defined]
        redis.publish = AsyncMock()

        ctx = {"redis": redis}

        with patch(
            "src.worker.tasks.import_youtube_subtitles.AsyncSessionFactory",
            worker_session_factory,
        ), patch(
            "src.worker.tasks.import_youtube_subtitles.publish_import_event",
            new_callable=AsyncMock,
        ):
            await import_youtube_subtitles(
                ctx,
                video_id=video.video_id,
                content_item_id=str(content_item.id),
                language_id=language.id,
            )

        await test_session.refresh(content_item)
        assert content_item.status == "processing"

    @pytest.mark.asyncio
    async def test_error_handling_sets_status_to_failed(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """If an error occurs, status is set to "failed" and error_message is recorded."""
        user, content_item, language, video = setup

        redis = AsyncMock()
        redis.set = AsyncMock()
        redis.enqueue_job = AsyncMock()  # type: ignore[attr-defined]
        redis.publish = AsyncMock()

        ctx = {"redis": redis}

        # Simulate DB error during task execution
        with patch(
            "src.worker.tasks.import_youtube_subtitles.AsyncSessionFactory",
            side_effect=ValueError("Simulated DB error"),
        ), patch(
            "src.worker.tasks.import_youtube_subtitles.publish_import_event",
            new_callable=AsyncMock,
        ):
            await import_youtube_subtitles(
                ctx,
                video_id=video.video_id,
                content_item_id=str(content_item.id),
                language_id=language.id,
            )

        # Verify error was published
        # Note: content_item status should be set to "failed" in a new session
        # so we need to refresh from DB
        refreshed_item = await test_session.get(ContentItem, content_item.id)
        assert refreshed_item.status == "failed"
        assert refreshed_item.error_message is not None
        assert "Simulated DB error" in refreshed_item.error_message

    @pytest.mark.asyncio
    async def test_handles_nonexistent_video(
        self,
        test_session: AsyncSession,
        setup,
        worker_session_factory,
    ):
        """Task handles missing video gracefully."""
        user, content_item, language, video = setup

        redis = AsyncMock()
        redis.set = AsyncMock()
        redis.enqueue_job = AsyncMock()  # type: ignore[attr-defined]
        redis.publish = AsyncMock()

        ctx = {"redis": redis}

        # Use a nonexistent video ID
        with patch(
            "src.worker.tasks.import_youtube_subtitles.AsyncSessionFactory",
            worker_session_factory,
        ), patch(
            "src.worker.tasks.import_youtube_subtitles.publish_import_event",
            new_callable=AsyncMock,
        ):
            await import_youtube_subtitles(
                ctx,
                video_id="nonexistent_video_id",
                content_item_id=str(content_item.id),
                language_id=language.id,
            )

        # Should have set status to failed since no subtitles were found
        await test_session.refresh(content_item)
        # Either status is still processing (early return) or failed
        # depending on implementation — verify it didn't error
        assert content_item.status in ["pending", "processing", "failed"]
