"""Tests for YouTube import API routes."""
import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yt_dlp
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.content import ContentItem
from src.infrastructure.db.models.users import User
from src.infrastructure.db.models.youtube import YouTubeVideo
from src.infrastructure.db.repositories.content_repo import ContentRepository
from src.infrastructure.db.repositories.youtube_repo import YouTubeRepository


class TestYouTubePreviewEndpoint:
    """Test GET /youtube/preview endpoint."""

    @pytest.mark.asyncio
    async def test_preview_success(self, test_client: AsyncClient):
        """Test successful video preview."""
        mock_metadata = {
            "video_id": "test123",
            "title": "Test Video",
            "duration_ms": 300000,
            "channel_name": "Test Channel",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "available_subtitles": [
                {"lang_code": "en", "label": "English", "is_auto": False},
                {"lang_code": "es", "label": "Spanish", "is_auto": True},
            ],
        }

        with patch("src.api.routes.youtube._fetcher.fetch_metadata") as mock_fetch:
            mock_fetch.return_value = mock_metadata

            response = await test_client.get(
                "/youtube/preview?url=https://www.youtube.com/watch?v=test123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["video_id"] == "test123"
            assert data["title"] == "Test Video"
            assert data["duration_ms"] == 300000
            assert len(data["available_subtitles"]) == 2

    @pytest.mark.asyncio
    async def test_preview_missing_url(self, test_client: AsyncClient):
        """Test preview without URL parameter."""
        response = await test_client.get("/youtube/preview")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_preview_invalid_url(self, test_client: AsyncClient):
        """Test preview with invalid YouTube URL."""
        with patch("src.api.routes.youtube._fetcher.fetch_metadata") as mock_fetch:
            mock_fetch.side_effect = yt_dlp.utils.DownloadError("Invalid URL")

            response = await test_client.get(
                "/youtube/preview?url=https://invalid.com/video"
            )

            assert response.status_code == 400
            assert "Failed to fetch video" in response.json()["detail"]


class TestYouTubeImportEndpoint:
    """Test POST /youtube/import endpoint."""

    @pytest.mark.asyncio
    async def test_import_success(
        self, test_client: AsyncClient, test_user_factory, test_language_factory, test_session
    ):
        """Test successful YouTube import."""
        # Setup: create user and language
        user = await test_user_factory(email="import@example.com")
        language, _, _ = await test_language_factory(code="en", name="English")
        user.active_language_id = language.id
        await test_session.commit()

        # Mock metadata and subtitles
        mock_metadata = {
            "video_id": "import123",
            "title": "Test Import",
            "duration_ms": 300000,
            "channel_name": "Test Channel",
            "thumbnail_url": None,
            "available_subtitles": [],
        }

        mock_subtitles = [
            {"line_number": 1, "start_ms": 1000, "end_ms": 3500, "text": "Hello"},
            {"line_number": 2, "start_ms": 4000, "end_ms": 6000, "text": "World"},
        ]

        # Mock ARQ pool
        mock_arq = AsyncMock()
        mock_arq.enqueue_job = AsyncMock()

        with patch(
            "src.api.routes.youtube._fetcher.fetch_metadata"
        ) as mock_fetch_meta, patch(
            "src.api.routes.youtube._fetcher.fetch_subtitles"
        ) as mock_fetch_subs, patch(
            "src.api.routes.youtube.get_arq_pool"
        ) as mock_get_arq:
            mock_fetch_meta.return_value = mock_metadata
            mock_fetch_subs.return_value = mock_subtitles
            mock_get_arq.return_value = mock_arq

            # Get auth token
            login_response = await test_client.post(
                "/auth/login",
                json={"email": "import@example.com", "password": "password123"},
            )
            token = login_response.json()["access_token"]

            # Test import
            response = await test_client.post(
                "/youtube/import",
                json={
                    "url": "https://www.youtube.com/watch?v=import123",
                    "title": "Test Import",
                    "language_id": language.id,
                    "subtitle_lang_code": "en",
                    "use_auto_captions": False,
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 202
            data = response.json()
            assert data["video_id"] == "import123"
            assert data["status"] == "in_progress"
            assert mock_arq.enqueue_job.called

    @pytest.mark.asyncio
    async def test_import_unauthenticated(self, test_client: AsyncClient):
        """Test import without authentication."""
        response = await test_client.post(
            "/youtube/import",
            json={
                "url": "https://www.youtube.com/watch?v=test",
                "title": "Test",
                "language_id": 1,
                "subtitle_lang_code": "en",
                "use_auto_captions": False,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_import_invalid_url(self, test_client: AsyncClient, test_user_factory, test_language_factory, test_session):
        """Test import with invalid YouTube URL."""
        user = await test_user_factory(email="invalid@example.com")
        language, _, _ = await test_language_factory()
        user.active_language_id = language.id
        await test_session.commit()

        with patch("src.api.routes.youtube._fetcher.fetch_metadata") as mock_fetch:
            mock_fetch.side_effect = yt_dlp.utils.DownloadError("Invalid video")

            login_response = await test_client.post(
                "/auth/login",
                json={"email": "invalid@example.com", "password": "password123"},
            )
            token = login_response.json()["access_token"]

            response = await test_client.post(
                "/youtube/import",
                json={
                    "url": "https://invalid.url",
                    "title": "Test",
                    "language_id": language.id,
                    "subtitle_lang_code": "en",
                    "use_auto_captions": False,
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 400


class TestYouTubeSubtitleUploadEndpoint:
    """Test POST /youtube/{video_id}/subtitles/upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_success(
        self, test_client: AsyncClient, test_user_factory, test_language_factory, test_session
    ):
        """Test successful SRT file upload."""
        # Setup user and create a YouTube video
        user = await test_user_factory(email="upload@example.com")
        language, _, _ = await test_language_factory()
        user.active_language_id = language.id
        await test_session.commit()

        # Create a content item and YouTube video
        content_repo = ContentRepository()
        youtube_repo = YouTubeRepository()

        content_item = await content_repo.create_content_item(
            session=test_session,
            user_id=user.id,
            language_id=language.id,
            type="youtube",
            title="Test Video",
        )
        await test_session.flush()

        await youtube_repo.create_video(
            session=test_session,
            id=content_item.id,
            video_id="upload123",
            youtube_url="https://www.youtube.com/watch?v=upload123",
        )
        await test_session.commit()

        # Create .srt file content
        srt_content = """1
00:00:01,000 --> 00:00:03,500
Hello

2
00:00:04,000 --> 00:00:06,000
World
"""

        srt_file = io.BytesIO(srt_content.encode("utf-8"))

        # Get auth token
        login_response = await test_client.post(
            "/auth/login",
            json={"email": "upload@example.com", "password": "password123"},
        )
        token = login_response.json()["access_token"]

        # Upload subtitles
        response = await test_client.post(
            "/youtube/upload123/subtitles/upload",
            files={"file": ("subs.srt", srt_file, "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "upload123"
        assert data["status"] == "in_progress"
        assert data["lines_parsed"] == 2

    @pytest.mark.asyncio
    async def test_upload_video_not_found(self, test_client: AsyncClient, test_user_factory, test_language_factory, test_session):
        """Test upload for non-existent video."""
        user = await test_user_factory(email="notfound@example.com")
        language, _, _ = await test_language_factory()
        user.active_language_id = language.id
        await test_session.commit()

        srt_file = io.BytesIO(b"1\n00:00:01,000 --> 00:00:02,000\nTest\n")

        login_response = await test_client.post(
            "/auth/login",
            json={"email": "notfound@example.com", "password": "password123"},
        )
        token = login_response.json()["access_token"]

        response = await test_client.post(
            "/youtube/nonexistent123/subtitles/upload",
            files={"file": ("subs.srt", srt_file, "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_invalid_srt(self, test_client: AsyncClient, test_user_factory, test_language_factory, test_session):
        """Test upload with invalid SRT content."""
        user = await test_user_factory(email="invalidsrt@example.com")
        language, _, _ = await test_language_factory()
        user.active_language_id = language.id
        await test_session.commit()

        # Create a video
        content_repo = ContentRepository()
        youtube_repo = YouTubeRepository()

        content_item = await content_repo.create_content_item(
            session=test_session,
            user_id=user.id,
            language_id=language.id,
            type="youtube",
            title="Test",
        )
        await test_session.flush()

        await youtube_repo.create_video(
            session=test_session,
            id=content_item.id,
            video_id="invtest123",
            youtube_url="https://www.youtube.com/watch?v=invtest123",
        )
        await test_session.commit()

        # Upload invalid SRT (empty file)
        srt_file = io.BytesIO(b"")

        login_response = await test_client.post(
            "/auth/login",
            json={"email": "invalidsrt@example.com", "password": "password123"},
        )
        token = login_response.json()["access_token"]

        response = await test_client.post(
            "/youtube/invtest123/subtitles/upload",
            files={"file": ("subs.srt", srt_file, "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "No valid subtitle lines found" in response.json()["detail"]
