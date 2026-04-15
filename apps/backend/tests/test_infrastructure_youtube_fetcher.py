"""Tests for YouTube metadata fetcher."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yt_dlp

from src.infrastructure.youtube.fetcher import YouTubeMetadataFetcher, _get_language_label


class TestYouTubeMetadataFetcher:
    """Test YouTube metadata fetching."""

    def test_fetch_metadata_success(self):
        """Test successful metadata fetch."""
        fetcher = YouTubeMetadataFetcher()

        mock_info = {
            "id": "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up",
            "duration": 212.5,
            "uploader": "Official Rick Astley",
            "thumbnail": "https://example.com/thumb.jpg",
            "subtitles": {
                "en": [{"url": "https://example.com/en.srt"}],
                "es": [{"url": "https://example.com/es.srt"}],
            },
            "automatic_captions": {
                "fr": [{"url": "https://example.com/fr_auto.srt"}],
            },
        }

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_info
            mock_ydl_class.return_value = mock_ydl

            result = fetcher.fetch_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

            assert result["video_id"] == "dQw4w9WgXcQ"
            assert result["title"] == "Rick Astley - Never Gonna Give You Up"
            assert result["duration_ms"] == 212500
            assert result["channel_name"] == "Official Rick Astley"
            assert result["thumbnail_url"] == "https://example.com/thumb.jpg"
            assert len(result["available_subtitles"]) == 3

            # Check subtitle tracks
            auto_subs = [s for s in result["available_subtitles"] if s["is_auto"]]
            user_subs = [s for s in result["available_subtitles"] if not s["is_auto"]]
            assert len(auto_subs) == 1
            assert len(user_subs) == 2

    def test_fetch_metadata_no_duration(self):
        """Test metadata fetch when duration is None."""
        fetcher = YouTubeMetadataFetcher()

        mock_info = {
            "id": "test123",
            "title": "Test Video",
            "duration": None,
            "uploader": "Test Channel",
            "thumbnail": None,
            "subtitles": {},
            "automatic_captions": {},
        }

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_info
            mock_ydl_class.return_value = mock_ydl

            result = fetcher.fetch_metadata("https://www.youtube.com/watch?v=test123")

            assert result["duration_ms"] is None

    def test_fetch_metadata_download_error(self):
        """Test metadata fetch when yt-dlp fails."""
        fetcher = YouTubeMetadataFetcher()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Video not found")
            mock_ydl_class.return_value = mock_ydl

            with pytest.raises(yt_dlp.utils.DownloadError):
                fetcher.fetch_metadata("https://www.youtube.com/watch?v=invalid")

    def test_fetch_metadata_invalid_video_id(self):
        """Test metadata fetch with invalid video ID (too long)."""
        fetcher = YouTubeMetadataFetcher()

        mock_info = {
            "id": "this_is_way_too_long_to_be_a_valid_youtube_id",
            "title": "Test",
            "duration": 100,
            "uploader": "Test",
            "thumbnail": None,
            "subtitles": {},
            "automatic_captions": {},
        }

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_info
            mock_ydl_class.return_value = mock_ydl

            with pytest.raises(ValueError, match="Invalid video ID"):
                fetcher.fetch_metadata("https://www.youtube.com/watch?v=test")

    def test_fetch_subtitles_success(self):
        """Test successful subtitle fetching."""
        fetcher = YouTubeMetadataFetcher()

        mock_info = {"id": "dQw4w9WgXcQ"}
        srt_content = """1
00:00:01,000 --> 00:00:03,500
Hello world

2
00:00:04,000 --> 00:00:06,000
How are you?
"""

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_info
            mock_ydl_class.return_value = mock_ydl

            with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
                temp_path = MagicMock()
                temp_path.__enter__ = MagicMock(return_value="/tmp/test")
                temp_path.__exit__ = MagicMock(return_value=False)
                mock_temp_dir.return_value = temp_path

                with patch("pathlib.Path.glob") as mock_glob:
                    srt_file = MagicMock()
                    srt_file.read_text.return_value = srt_content
                    mock_glob.return_value = [srt_file]

                    result = fetcher.fetch_subtitles(
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        "en",
                        use_auto=False,
                    )

                    assert len(result) == 2
                    assert result[0]["text"] == "Hello world"
                    assert result[1]["text"] == "How are you?"

    def test_fetch_subtitles_no_file_found(self):
        """Test subtitle fetching when no .srt file is downloaded."""
        fetcher = YouTubeMetadataFetcher()

        mock_info = {"id": "test123"}

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_info
            mock_ydl_class.return_value = mock_ydl

            with patch("tempfile.TemporaryDirectory") as mock_temp_dir:
                temp_path = MagicMock()
                temp_path.__enter__ = MagicMock(return_value="/tmp/test")
                temp_path.__exit__ = MagicMock(return_value=False)
                mock_temp_dir.return_value = temp_path

                with patch("pathlib.Path.glob") as mock_glob:
                    mock_glob.return_value = []  # No files found

                    with pytest.raises(ValueError, match="No subtitles found"):
                        fetcher.fetch_subtitles(
                            "https://www.youtube.com/watch?v=test123",
                            "en",
                        )


class TestGetLanguageLabel:
    """Test language code to label conversion."""

    def test_known_language_codes(self):
        """Test conversion of known language codes."""
        assert _get_language_label("en") == "English"
        assert _get_language_label("es") == "Spanish"
        assert _get_language_label("fr") == "French"
        assert _get_language_label("de") == "German"
        assert _get_language_label("ru") == "Russian"
        assert _get_language_label("ja") == "Japanese"
        assert _get_language_label("zh") == "Chinese"

    def test_unknown_language_code(self):
        """Test conversion of unknown language codes."""
        assert _get_language_label("xyz") == "XYZ"
        assert _get_language_label("xx") == "XX"
