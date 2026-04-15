"""EmbeddedAudioExtractor — pull audio files out of an EPUB zip.

Extracts all audio files referenced by SMIL overlays to
``storage_root/books/{book_id}/audio/``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
import zipfile

logger = logging.getLogger(__name__)

_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg", ".wav", ".flac", ".opus"}


class EmbeddedAudioExtractor:
    async def extract(
        self,
        epub_path: str,
        book_id: uuid.UUID,
        storage_root: str,
        audio_files: list[str],
    ) -> dict[str, str]:
        """Extract audio items from the EPUB to disk.

        Args:
            epub_path: absolute path to the .epub file
            book_id: used to construct the output directory
            storage_root: base storage directory
            audio_files: EPUB-root-relative paths to extract
                         (as returned by SmilParser.list_audio_files)

        Returns:
            Mapping of EPUB-root-relative path → absolute local path.
        """
        out_dir = os.path.join(storage_root, "books", str(book_id), "audio")
        os.makedirs(out_dir, exist_ok=True)

        return await asyncio.to_thread(
            self._extract_sync, epub_path, audio_files, out_dir
        )

    def _extract_sync(
        self,
        epub_path: str,
        audio_files: list[str],
        out_dir: str,
    ) -> dict[str, str]:
        result: dict[str, str] = {}

        with zipfile.ZipFile(epub_path, "r") as zf:
            # Build a case-insensitive lookup: filename_in_zip (lower) → actual name
            zip_names_lower = {n.lower(): n for n in zf.namelist()}

            for epub_rel in audio_files:
                # Try direct match first, then case-insensitive
                zip_entry = self._find_entry(zf, epub_rel, zip_names_lower)
                if zip_entry is None:
                    logger.warning("Audio entry not found in EPUB: %s", epub_rel)
                    continue

                # Use the basename as the local filename
                local_name = os.path.basename(epub_rel)
                local_path = os.path.join(out_dir, local_name)

                data = zf.read(zip_entry)
                with open(local_path, "wb") as f:
                    f.write(data)

                result[epub_rel] = local_path
                logger.info("Extracted audio: %s → %s", epub_rel, local_path)

        return result

    def _find_entry(
        self,
        zf: zipfile.ZipFile,
        epub_rel: str,
        zip_names_lower: dict[str, str],
    ) -> str | None:
        """Find a zip entry by EPUB-root-relative path (tries OPF subdirs automatically)."""
        candidates = [
            epub_rel,
            f"OEBPS/{epub_rel}",
            f"OPS/{epub_rel}",
        ]
        for candidate in candidates:
            if candidate in zf.namelist():
                return candidate
            lower = candidate.lower()
            if lower in zip_names_lower:
                return zip_names_lower[lower]
        return None
