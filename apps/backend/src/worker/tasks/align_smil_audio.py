"""align_smil_audio — ARQ task for EPUB3 SMIL audio overlay alignment.

Maps SMIL overlay timings to (page_id, sentence_index) pairs and stores
them in the sentence_alignments table.
"""

from __future__ import annotations

import json
import logging
import os
import uuid

import sqlalchemy as sa
from redis.asyncio import Redis

from src.core.config import get_settings
from src.domain.audio.extractor import EmbeddedAudioExtractor
from src.domain.audio.fragment_resolver import FragmentResolver
from src.domain.audio.smil_parser import SmilParser
from src.domain.content.import_service import AUDIO_ALIGN_CHANNEL
from src.infrastructure.db.engine import AsyncSessionFactory
from src.infrastructure.db.models.content import Book, ContentPage
from src.infrastructure.db.repositories.audio_repo import AudioRepository

logger = logging.getLogger(__name__)

_audio_repo = AudioRepository()
_smil_parser = SmilParser()
_extractor = EmbeddedAudioExtractor()
_settings = get_settings()


async def align_smil_audio(ctx: dict, book_id: str) -> None:
    book_uuid = uuid.UUID(book_id)
    redis: Redis = ctx["redis"]

    async with AsyncSessionFactory() as session:
        book = await session.get(Book, book_uuid)
        if book is None:
            logger.error("Book %s not found", book_uuid)
            return

        epub_path = os.path.join(_settings.storage_root, book.file_path)
        if not os.path.exists(epub_path):
            logger.error("EPUB file not found: %s", epub_path)
            book.audio_overlay_status = "failed"
            await session.commit()
            return

        book.audio_overlay_status = "in_progress"
        await session.commit()

    logger.info("SMIL alignment starting for book %s", book_uuid)

    try:
        # Parse SMIL — extract all (xhtml, fragment_id, audio, start_ms, end_ms)
        fragments = _smil_parser.parse_epub(epub_path)
        if not fragments:
            raise RuntimeError("No SMIL fragments found in EPUB")

        audio_files = _smil_parser.list_audio_files(epub_path)

        # Extract embedded audio to disk
        audio_map = await _extractor.extract(
            epub_path=epub_path,
            book_id=book_uuid,
            storage_root=_settings.storage_root,
            audio_files=audio_files,
        )

        # Set audio_file_path to the first extracted audio file
        first_audio_path: str | None = next(iter(audio_map.values()), None)

        # Build sentence index: xhtml_file → [(page_id, sentence_index, sentence_text)]
        async with AsyncSessionFactory() as session:
            rows = await session.execute(
                sa.select(ContentPage.id, ContentPage.xhtml_file, ContentPage.text)
                .where(ContentPage.content_item_id == book_uuid, ContentPage.status == "ready")
                .order_by(ContentPage.page_number)
            )
            pages = list(rows)

        xhtml_index: dict[str, list[tuple[uuid.UUID, int, str]]] = {}
        for page_id, xhtml_file, text in pages:
            if xhtml_file is None:
                continue
            sentences = [s.strip() for s in text.replace("\n\n", "\n").split("\n") if s.strip()]
            for si, sentence in enumerate(sentences):
                xhtml_index.setdefault(xhtml_file, []).append((page_id, si, sentence))

        # Resolve each SMIL fragment to (page_id, sentence_index)
        resolver = FragmentResolver(epub_path)
        alignments_by_page: dict[uuid.UUID, list[dict]] = {}
        # Split unresolved counter by failure mode so we can tell which to fix.
        id_not_found = 0
        sentence_not_matched = 0
        # Keep up to N samples of each failure mode for diagnostics.
        _SAMPLE_CAP = 5
        id_samples: list[str] = []
        sent_samples: list[str] = []

        # Build epub_rel → storage-relative path mapping
        storage_audio_map: dict[str, str] = {
            epub_rel: os.path.relpath(abs_path, _settings.storage_root)
            for epub_rel, abs_path in audio_map.items()
        }

        for frag in fragments:
            frag_text = resolver.resolve_text(frag.xhtml_file, frag.fragment_id)
            if frag_text is None:
                id_not_found += 1
                if len(id_samples) < _SAMPLE_CAP:
                    id_samples.append(f"{frag.xhtml_file}#{frag.fragment_id}")
                continue

            candidates = xhtml_index.get(frag.xhtml_file, [])
            match = _find_sentence(frag_text, candidates)
            if match is None:
                sentence_not_matched += 1
                if len(sent_samples) < _SAMPLE_CAP:
                    snippet = (frag_text[:80] + "…") if len(frag_text) > 80 else frag_text
                    sent_samples.append(
                        f"{frag.xhtml_file}#{frag.fragment_id} "
                        f"({len(candidates)} candidates): {snippet!r}"
                    )
                continue

            page_id, si = match
            alignments_by_page.setdefault(page_id, []).append(
                {
                    "sentence_index": si,
                    "audio_start_ms": frag.audio_start_ms,
                    "audio_end_ms": frag.audio_end_ms,
                    "audio_file": storage_audio_map.get(frag.audio_file),
                }
            )

        unresolved = id_not_found + sentence_not_matched
        if unresolved:
            logger.warning(
                "SMIL alignment: %d unresolved (id_not_found=%d, sentence_not_matched=%d)",
                unresolved, id_not_found, sentence_not_matched,
            )
            for sample in id_samples:
                logger.warning("  id_not_found sample: %s", sample)
            for sample in sent_samples:
                logger.warning("  sentence_not_matched sample: %s", sample)

        # Check if cancelled while we were processing
        if await redis.exists(AUDIO_ALIGN_CHANNEL.format(book_id=book_uuid) + ":cancel"):
            logger.info("SMIL alignment cancelled for book %s — discarding results", book_uuid)
            return

        # Persist alignments
        async with AsyncSessionFactory() as session:
            for page_id, page_alignments in alignments_by_page.items():
                await _audio_repo.upsert_alignments(session, page_id, page_alignments)

            book = await session.get(Book, book_uuid)
            if book:
                book.audio_overlay_status = "complete"
                if first_audio_path:
                    rel = os.path.relpath(first_audio_path, _settings.storage_root)
                    book.audio_file_path = rel
            await session.commit()

        total = sum(len(v) for v in alignments_by_page.values())
        logger.info(
            "SMIL alignment complete for book %s: %d alignments, %d unresolved",
            book_uuid, total, unresolved,
        )

        await redis.publish(
            AUDIO_ALIGN_CHANNEL.format(book_id=book_uuid),
            json.dumps({"event": "complete", "data": {"sentences": total}}),
        )

    except Exception as exc:
        logger.exception("SMIL alignment failed for book %s: %s", book_uuid, exc)
        async with AsyncSessionFactory() as session:
            book = await session.get(Book, book_uuid)
            if book:
                book.audio_overlay_status = "failed"
            await session.commit()
        await redis.publish(
            AUDIO_ALIGN_CHANNEL.format(book_id=book_uuid),
            json.dumps({"event": "failed", "data": {"error": str(exc)}}),
        )


def _find_sentence(
    frag_text: str,
    candidates: list[tuple[uuid.UUID, int, str]],
) -> tuple[uuid.UUID, int] | None:
    """Find the best-matching (page_id, sentence_index) for a fragment text."""
    frag_norm = _normalise(frag_text)
    best: tuple[uuid.UUID, int] | None = None
    best_score = 0

    for page_id, si, sentence in candidates:
        sent_norm = _normalise(sentence)
        # Exact match
        if frag_norm == sent_norm:
            return page_id, si
        # Substring match (SMIL fragment may be a prefix/suffix of merged sentence)
        if frag_norm in sent_norm or sent_norm in frag_norm:
            score = min(len(frag_norm), len(sent_norm))
            if score > best_score:
                best_score = score
                best = page_id, si

    return best


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())
