"""Audio clipping via ffmpeg subprocess."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

_ffmpeg_path: str | None = shutil.which("ffmpeg")


def is_available() -> bool:
    """Check if ffmpeg is installed and accessible."""
    return _ffmpeg_path is not None


def clip_audio(audio_file_path: str, start_ms: int, end_ms: int) -> bytes | None:
    """Clip a segment from an audio file and return MP3 bytes.

    Returns None if ffmpeg is unavailable, the file doesn't exist, or clipping fails.
    """
    if not _ffmpeg_path:
        logger.warning("ffmpeg not found — skipping audio clip")
        return None

    start_s = start_ms / 1000.0
    duration_s = (end_ms - start_ms) / 1000.0
    if duration_s <= 0:
        return None

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
            result = subprocess.run(
                [
                    _ffmpeg_path,
                    "-y",
                    "-ss", f"{start_s:.3f}",
                    "-t", f"{duration_s:.3f}",
                    "-i", audio_file_path,
                    "-acodec", "libmp3lame",
                    "-ab", "64k",
                    "-ac", "1",
                    "-ar", "22050",
                    "-f", "mp3",
                    tmp.name,
                ],
                capture_output=True,
                timeout=15,
            )
            if result.returncode != 0:
                logger.warning("ffmpeg clip failed: %s", result.stderr[:200])
                return None

            tmp.seek(0)
            return tmp.read()
    except FileNotFoundError:
        logger.warning("Audio file not found: %s", audio_file_path)
        return None
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg timeout clipping %s", audio_file_path)
        return None
