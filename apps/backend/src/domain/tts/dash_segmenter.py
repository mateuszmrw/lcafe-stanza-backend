"""DashSegmenter — concatenate per-sentence MP3s and produce an MPEG-DASH stream.

Uses ffmpeg/ffprobe via asyncio.create_subprocess_exec (no shell, no injection risk).
All paths are internal — never constructed from user input.
"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_SEGMENT_DURATION = 4  # seconds per DASH chunk


class DashSegmenter:
    async def build(
        self,
        audio_files: list[tuple[str, int]],  # (abs_path, duration_ms)
        output_dir: str,
    ) -> tuple[str, list[int]]:
        """Concatenate audio files and produce a DASH manifest.

        Returns:
            (manifest_abs_path, sentence_start_ms_list)
        """
        os.makedirs(output_dir, exist_ok=True)

        # Cumulative start timestamps from cached durations
        starts: list[int] = []
        cursor = 0
        for _, duration_ms in audio_files:
            starts.append(cursor)
            cursor += duration_ms

        concat_list = os.path.join(output_dir, "_concat.txt")
        with open(concat_list, "w") as f:
            for abs_path, _ in audio_files:
                f.write(f"file '{abs_path}'\n")

        manifest_path = os.path.join(output_dir, "manifest.mpd")
        try:
            await self._ffmpeg(
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list,
                "-c:a", "aac",
                "-b:a", "64k",
                "-f", "dash",
                "-seg_duration", str(_SEGMENT_DURATION),
                "-adaptation_sets", "id=0,streams=a",
                "-y", manifest_path,
            )
        finally:
            try:
                os.remove(concat_list)
            except OSError:
                pass

        return manifest_path, starts

    async def get_duration_ms(self, audio_path: str) -> int:
        """Return duration of an audio file in milliseconds via ffprobe."""
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("ffprobe failed for %s", audio_path)
            return 0
        try:
            return int(float(stdout.decode().strip()) * 1000)
        except (ValueError, AttributeError):
            return 0

    async def _ffmpeg(self, *args: str) -> None:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-loglevel", "error", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {stderr.decode(errors='replace')}")
