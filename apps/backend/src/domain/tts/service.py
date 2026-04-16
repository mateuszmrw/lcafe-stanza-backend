"""TtsService — orchestrate TTS generation, caching, and DASH packaging."""

from __future__ import annotations

import hashlib
import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.domain.tts.dash_segmenter import DashSegmenter
from src.infrastructure.db.repositories.tts_cache_repo import TtsCacheRepository
from src.infrastructure.tts.providers.openai_tts import OpenAITtsProvider

logger = logging.getLogger(__name__)


class TtsService:
    def __init__(self) -> None:
        self._provider = OpenAITtsProvider()
        self._cache_repo = TtsCacheRepository()
        self._segmenter = DashSegmenter()

    def supports_language(self, language_code: str) -> bool:
        return self._provider.supports(language_code)

    async def get_or_generate_sentence(
        self,
        session: AsyncSession,
        text: str,
        language_code: str,
    ) -> tuple[str, int] | None:
        """Return (storage_relative_path, duration_ms) for a sentence, generating if needed.

        Returns None if the language is unsupported.
        """
        if not self.supports_language(language_code):
            return None

        text_normalized = " ".join(text.split())
        text_hash = hashlib.sha256(
            f"{language_code}:{text_normalized}".encode()
        ).hexdigest()

        cached = await self._cache_repo.get_cached(session, language_code, text_hash)
        if cached:
            return cached.audio_file, cached.duration_ms

        # Generate and persist
        settings = get_settings()
        audio_bytes = await self._provider.generate(text_normalized, language_code)

        rel_path = os.path.join("tts", language_code, f"{text_hash}.mp3")
        abs_path = os.path.join(settings.storage_root, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "wb") as f:
            f.write(audio_bytes)

        duration_ms = await self._segmenter.get_duration_ms(abs_path)
        await self._cache_repo.upsert(session, language_code, text_hash, rel_path, duration_ms)

        return rel_path, duration_ms

    async def build_page_dash(
        self,
        session: AsyncSession,
        book_id: uuid.UUID,
        page_number: int,
        sentences: list[str],
        language_code: str,
    ) -> tuple[str, list[tuple[int, int]]] | None:
        """Generate a DASH manifest for a page's sentences.

        Returns (manifest_storage_relative_path, [(start_ms, end_ms), ...]) or None
        if the language is unsupported or no sentences could be synthesised.
        """
        settings = get_settings()
        audio_entries: list[tuple[str, int]] = []

        for sentence in sentences:
            if not sentence.strip():
                continue
            result = await self.get_or_generate_sentence(session, sentence, language_code)
            if result is None:
                return None
            rel_path, duration_ms = result
            abs_path = os.path.join(settings.storage_root, rel_path)
            audio_entries.append((abs_path, duration_ms))

        if not audio_entries:
            return None

        output_dir = os.path.join(
            settings.storage_root,
            "books",
            str(book_id),
            "tts",
            str(page_number),
        )
        manifest_abs, starts = await self._segmenter.build(audio_entries, output_dir)
        manifest_rel = os.path.relpath(manifest_abs, settings.storage_root)

        alignments: list[tuple[int, int]] = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else start + audio_entries[i][1]
            alignments.append((start, end))

        return manifest_rel, alignments
