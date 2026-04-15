"""YouTube metadata and subtitle fetcher using yt-dlp."""
import logging
import tempfile
from pathlib import Path

import yt_dlp  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class YouTubeMetadataFetcher:
    """Fetch metadata and subtitles from YouTube videos."""

    def fetch_metadata(self, url: str) -> dict:
        """Fetch video metadata including title, duration, and available subtitles.

        Args:
            url: YouTube video URL

        Returns:
            Dict with keys: video_id, title, duration_ms, channel_name, thumbnail_url,
            available_subtitles (list of {lang_code, label, is_auto})

        Raises:
            yt_dlp.utils.DownloadError: If video cannot be fetched
        """
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Failed to fetch YouTube metadata for {url}: {e}")
            raise

        # Extract video ID (11-character format)
        video_id = info.get("id", "")
        if not video_id or len(video_id) > 11:
            raise ValueError(f"Invalid video ID: {video_id}")

        duration_s = info.get("duration", 0) or 0
        duration_ms = int(duration_s * 1000) if duration_s else None

        # Build available subtitles list
        available_subtitles = []
        subtitles_dict = info.get("subtitles", {})
        automatic_captions = info.get("automatic_captions", {})

        # User-uploaded subtitles
        for lang_code, subs in subtitles_dict.items():
            if subs:
                available_subtitles.append({
                    "lang_code": lang_code,
                    "label": _get_language_label(lang_code),
                    "is_auto": False,
                })

        # Auto-generated captions
        for lang_code, subs in automatic_captions.items():
            if subs:
                available_subtitles.append({
                    "lang_code": lang_code,
                    "label": _get_language_label(lang_code),
                    "is_auto": True,
                })

        return {
            "video_id": video_id,
            "title": info.get("title", ""),
            "duration_ms": duration_ms,
            "channel_name": info.get("uploader", ""),
            "thumbnail_url": info.get("thumbnail", ""),
            "available_subtitles": available_subtitles,
        }

    def fetch_subtitles(
        self, url: str, lang_code: str, use_auto: bool = False
    ) -> list[dict]:
        """Fetch and parse subtitles for a video.

        Args:
            url: YouTube video URL
            lang_code: Subtitle language code (e.g. "en", "fr")
            use_auto: If True, use auto-generated captions if user-uploaded unavailable

        Returns:
            List of dicts with keys: line_number, start_ms, end_ms, text

        Raises:
            yt_dlp.utils.DownloadError: If video or subtitles cannot be fetched
            ValueError: If subtitles unavailable in requested language
        """
        from src.infrastructure.youtube.srt_parser import parse_srt

        # Download subtitles to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": use_auto,
                "subtitleslangs": [lang_code],
                "subtitlesformat": "srt",
                "quiet": True,
                "no_warnings": True,
                "outtmpl": str(Path(temp_dir) / "%(id)s.%(ext)s"),
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url, download=True)
            except Exception as e:
                logger.error(f"Failed to download subtitles for {url}: {e}")
                raise

            # Find the downloaded .srt file
            temp_path = Path(temp_dir)
            srt_files = list(temp_path.glob("*.srt"))

            if not srt_files:
                raise ValueError(f"No subtitles found for language: {lang_code}")

            # Read and parse the SRT file
            srt_content = srt_files[0].read_text(encoding="utf-8")
            return parse_srt(srt_content)


def _get_language_label(lang_code: str) -> str:
    """Convert language code to human-readable label.

    Args:
        lang_code: Two-letter ISO language code (e.g. "en", "fr")

    Returns:
        Human-readable language name or the code if not recognized
    """
    language_names = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ja": "Japanese",
        "zh": "Chinese",
        "ko": "Korean",
        "ar": "Arabic",
        "hi": "Hindi",
        "pl": "Polish",
        "nl": "Dutch",
        "tr": "Turkish",
        "vi": "Vietnamese",
        "th": "Thai",
        "id": "Indonesian",
        "fil": "Filipino",
        "uk": "Ukrainian",
    }
    return language_names.get(lang_code, lang_code.upper())
