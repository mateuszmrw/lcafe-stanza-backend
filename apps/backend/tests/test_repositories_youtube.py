"""Tests for YouTube repository."""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.youtube import YouTubeSubtitle, YouTubeVideo
from src.infrastructure.db.repositories.youtube_repo import YouTubeRepository


class TestYouTubeRepository:
    """Test YouTube data operations."""

    @pytest.mark.asyncio
    async def test_create_video(self, test_session: AsyncSession):
        """Test creating a YouTube video record."""
        repo = YouTubeRepository()
        content_item_id = uuid.uuid4()

        video = await repo.create_video(
            session=test_session,
            id=content_item_id,
            video_id="dQw4w9WgXcQ",
            youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            channel_name="Official Rick Astley",
            video_duration_ms=212500,
            subtitle_lang_code="en",
            subtitle_source="user-uploaded",
        )
        await test_session.commit()

        assert video.id == content_item_id
        assert video.video_id == "dQw4w9WgXcQ"
        assert video.youtube_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert video.channel_name == "Official Rick Astley"

    @pytest.mark.asyncio
    async def test_find_by_video_id(self, test_session: AsyncSession):
        """Test finding video by ID."""
        repo = YouTubeRepository()
        content_item_id = uuid.uuid4()

        video = await repo.create_video(
            session=test_session,
            id=content_item_id,
            video_id="testVideoID",
            youtube_url="https://www.youtube.com/watch?v=testVideoID",
        )
        await test_session.commit()

        found = await repo.find_by_video_id(test_session, "testVideoID")
        assert found is not None
        assert found.id == content_item_id

    @pytest.mark.asyncio
    async def test_find_by_video_id_not_found(self, test_session: AsyncSession):
        """Test finding non-existent video."""
        repo = YouTubeRepository()

        found = await repo.find_by_video_id(test_session, "nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_create_subtitle(self, test_session: AsyncSession):
        """Test creating a single subtitle."""
        repo = YouTubeRepository()
        content_item_id = uuid.uuid4()

        # Create video first
        await repo.create_video(
            session=test_session,
            id=content_item_id,
            video_id="test123",
            youtube_url="https://www.youtube.com/watch?v=test123",
        )
        await test_session.commit()

        # Create subtitle
        subtitle = await repo.create_subtitle(
            session=test_session,
            video_id="test123",
            line_number=1,
            start_ms=1000,
            end_ms=3500,
            text="Hello world",
        )
        await test_session.commit()

        assert subtitle.video_id == "test123"
        assert subtitle.line_number == 1
        assert subtitle.start_ms == 1000
        assert subtitle.end_ms == 3500
        assert subtitle.text == "Hello world"

    @pytest.mark.asyncio
    async def test_create_subtitles_batch(self, test_session: AsyncSession):
        """Test creating multiple subtitles at once."""
        repo = YouTubeRepository()
        content_item_id = uuid.uuid4()

        # Create video first
        await repo.create_video(
            session=test_session,
            id=content_item_id,
            video_id="batch123",
            youtube_url="https://www.youtube.com/watch?v=batch123",
        )
        await test_session.commit()

        subtitles_data = [
            {"line_number": 1, "start_ms": 1000, "end_ms": 3500, "text": "Hello world"},
            {"line_number": 2, "start_ms": 4000, "end_ms": 6000, "text": "How are you?"},
            {"line_number": 3, "start_ms": 7000, "end_ms": 9000, "text": "I'm fine"},
        ]

        created = await repo.create_subtitles_batch(
            session=test_session,
            video_id="batch123",
            subtitles=subtitles_data,
        )
        await test_session.commit()

        assert len(created) == 3
        assert created[0].text == "Hello world"
        assert created[1].text == "How are you?"
        assert created[2].text == "I'm fine"

    @pytest.mark.asyncio
    async def test_delete_subtitles_for_video(self, test_session: AsyncSession):
        """Test deleting all subtitles for a video."""
        repo = YouTubeRepository()
        content_item_id = uuid.uuid4()

        # Create video and subtitles
        await repo.create_video(
            session=test_session,
            id=content_item_id,
            video_id="del123",
            youtube_url="https://www.youtube.com/watch?v=del123",
        )
        await test_session.commit()

        subtitles_data = [
            {"line_number": 1, "start_ms": 1000, "end_ms": 3500, "text": "Line 1"},
            {"line_number": 2, "start_ms": 4000, "end_ms": 6000, "text": "Line 2"},
        ]
        await repo.create_subtitles_batch(
            session=test_session,
            video_id="del123",
            subtitles=subtitles_data,
        )
        await test_session.commit()

        # Delete subtitles
        await repo.delete_subtitles_for_video(test_session, "del123")
        await test_session.commit()

        # Verify deletion
        subs = await repo.get_subtitles_for_video(test_session, "del123")
        assert len(subs) == 0

    @pytest.mark.asyncio
    async def test_get_subtitles_for_video(self, test_session: AsyncSession):
        """Test retrieving all subtitles for a video."""
        repo = YouTubeRepository()
        content_item_id = uuid.uuid4()

        # Create video and subtitles
        await repo.create_video(
            session=test_session,
            id=content_item_id,
            video_id="get123",
            youtube_url="https://www.youtube.com/watch?v=get123",
        )
        await test_session.commit()

        subtitles_data = [
            {"line_number": 1, "start_ms": 1000, "end_ms": 3500, "text": "First"},
            {"line_number": 2, "start_ms": 4000, "end_ms": 6000, "text": "Second"},
            {"line_number": 3, "start_ms": 7000, "end_ms": 9000, "text": "Third"},
        ]
        await repo.create_subtitles_batch(
            session=test_session,
            video_id="get123",
            subtitles=subtitles_data,
        )
        await test_session.commit()

        # Retrieve subtitles
        subs = await repo.get_subtitles_for_video(test_session, "get123")

        assert len(subs) == 3
        assert subs[0].text == "First"
        assert subs[1].text == "Second"
        assert subs[2].text == "Third"
