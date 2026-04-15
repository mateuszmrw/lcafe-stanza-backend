import base64
import csv
import io
import logging
import os
import uuid

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.api.schemas.vocabulary import BulkStatusUpdate, VocabularyStatusUpdate, VocabularyUpsertRequest, WordListResponse, WordResponse
from src.core.config import get_settings
from src.domain.coverage.service import invalidate_coverage_cache
from src.domain.difficulty.service import DifficultyService
from src.domain.stats.cache import invalidate_stats_cache
from src.infrastructure.anki.client import ensure_slovo_model, store_media_file
from src.infrastructure.anki.model_definition import SLOVO_MODEL_NAME
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.anki_repo import AnkiRepository
from src.infrastructure.db.repositories.audio_repo import AudioRepository
from src.infrastructure.db.repositories.dictionary_entry_repo import DictionaryEntryRepository
from src.infrastructure.db.repositories.word_frequency_repo import WordFrequencyRepository
from src.infrastructure.db.repositories.word_repo import WordRepository
from src.infrastructure.ffmpeg.clipper import clip_audio, is_available as ffmpeg_available

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])
_word_repo = WordRepository()
_anki_repo = AnkiRepository()
_dict_repo = DictionaryEntryRepository()
_freq_repo = WordFrequencyRepository()
_audio_repo = AudioRepository()
_difficulty_service = DifficultyService()


class RecordExposuresRequest(BaseModel):
    lemmas: list[str]
    language_id: int


class RecomputeDifficultyResponse(BaseModel):
    updated: int


class AnkiSyncRequest(BaseModel):
    language_id: int


class AnkiSyncResponse(BaseModel):
    synced: int
    queued: int
    pending_total: int



@router.get("", response_model=WordListResponse)
async def list_vocabulary(
    language_id: int,
    status: str | None = None,
    pos: str | None = None,
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WordListResponse:
    words, total = await _word_repo.list_paginated(
        session,
        user_id=current_user.id,
        language_id=language_id,
        status=status,
        pos=pos,
        page=page,
        limit=limit,
        search=search,
    )
    return WordListResponse(
        items=[WordResponse.model_validate(w) for w in words],
        total=total,
        page=page,
        limit=limit,
    )


@router.put("", response_model=WordResponse)
async def upsert_word_status(
    body: VocabularyUpsertRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> WordResponse:
    """Create a vocabulary entry if it doesn't exist, then set its status."""
    word = await _word_repo.upsert_with_status(
        session,
        user_id=current_user.id,
        language_id=body.language_id,
        word=body.word,
        status=body.status,
        lemma=body.lemma,
        pos=body.pos,
        reading=body.reading,
        gender=body.gender,
        feats=body.feats,
        hint=body.hint,
        sentence_context=body.sentence_context,
    )
    await session.commit()
    await invalidate_stats_cache(redis, current_user.id)
    await invalidate_coverage_cache(redis, current_user.id)
    return WordResponse.model_validate(word)


@router.post("/batch", status_code=204)
async def batch_upsert_word_status(
    body: list[VocabularyUpsertRequest],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Upsert status for multiple words in one request (e.g. auto-advance on page turn)."""
    rows = [
        {
            "user_id": current_user.id,
            "language_id": item.language_id,
            "word": item.word.lower().strip(),
            "status": item.status,
            "lemma": item.lemma,
            "pos": item.pos,
            "reading": item.reading,
            "gender": item.gender,
            "feats": item.feats,
        }
        for item in body
    ]
    await _word_repo.batch_upsert_status(session, rows)
    await session.commit()
    await invalidate_stats_cache(redis, current_user.id)
    await invalidate_coverage_cache(redis, current_user.id)


@router.patch("/bulk", status_code=204)
async def bulk_update_status(
    body: BulkStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Bulk-update status for multiple words owned by the current user."""
    await _word_repo.bulk_update_status(session, current_user.id, body.ids, body.status)
    await session.commit()
    await invalidate_stats_cache(redis, current_user.id)
    await invalidate_coverage_cache(redis, current_user.id)


@router.get("/export")
async def export_vocabulary(
    language_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all vocabulary for a language as a CSV file."""
    words = await _word_repo.list_all(session, user_id=current_user.id, language_id=language_id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["word", "lemma", "pos", "status", "hint", "lookup_count", "created_at"])
    for w in words:
        writer.writerow([
            w.word,
            w.lemma or "",
            w.pos or "",
            w.status,
            w.hint or "",
            w.lookup_count or 0,
            w.created_at.isoformat() if w.created_at else "",
        ])
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=vocabulary-{language_id}.csv"},
    )


@router.post("/record-exposures", status_code=204)
async def record_exposures(
    body: RecordExposuresRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Increment exposure_count for engaged words and recompute difficulty."""
    if not body.lemmas:
        return

    # Bulk increment exposure_count
    from src.infrastructure.db.models.words import Word
    await session.execute(
        sa.update(Word)
        .where(
            Word.user_id == current_user.id,
            Word.language_id == body.language_id,
            Word.word.in_(body.lemmas),
        )
        .values(exposure_count=Word.exposure_count + 1)
    )
    await session.commit()

    # Resolve language code for difficulty computation
    lang_row = await session.get(Language, body.language_id)
    lang_code = lang_row.code if lang_row else ""

    await _difficulty_service.recompute_for_words(
        session, current_user.id, body.language_id, lang_code, body.lemmas
    )
    await session.commit()


@router.post("/recompute-difficulty", response_model=RecomputeDifficultyResponse)
async def recompute_difficulty(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RecomputeDifficultyResponse:
    """Recompute difficulty scores for all words in the user's active language."""
    if not current_user.active_language_id:
        raise HTTPException(status_code=400, detail="No active language set")

    lang_row = await session.get(Language, current_user.active_language_id)
    lang_code = lang_row.code if lang_row else ""

    updated = await _difficulty_service.recompute_all(
        session, current_user.id, current_user.active_language_id, lang_code
    )
    await session.commit()
    return RecomputeDifficultyResponse(updated=updated)


@router.get("/anki-status", response_model=AnkiSyncResponse)
async def anki_status(
    language_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnkiSyncResponse:
    """Return current pending Anki sync count for this user+language."""
    pending_total = await _anki_repo.get_pending_count(session, current_user.id, language_id)
    return AnkiSyncResponse(synced=0, queued=0, pending_total=pending_total)


@router.get("/{word_id}", response_model=WordResponse)
async def get_word(
    word_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WordResponse:
    word = await _word_repo.find_by_id(session, word_id)
    if not word or word.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Word not found")
    return WordResponse.model_validate(word)


@router.patch("/{word_id}/status", response_model=WordResponse)
async def update_word_status(
    word_id: uuid.UUID,
    body: VocabularyStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> WordResponse:
    word = await _word_repo.find_by_id(session, word_id)
    if not word or word.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Word not found")

    updated = await _word_repo.update_status(session, word_id, body.status)
    await session.commit()
    await invalidate_stats_cache(redis, current_user.id)
    await invalidate_coverage_cache(redis, current_user.id)
    return WordResponse.model_validate(updated)


@router.post("/sync-anki", response_model=AnkiSyncResponse)
async def sync_to_anki(
    body: AnkiSyncRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnkiSyncResponse:
    """Sync learning vocabulary to Anki via AnkiConnect.

    Uses the custom 'Slovo' note model with rich fields: POS, gender,
    morphology, dictionary definition, frequency tier, sentence context,
    and audio clips from EPUB audiobooks.
    """
    anki_settings = await _anki_repo.get_settings(session)
    if not anki_settings.anki_connect_url:
        raise HTTPException(status_code=424, detail="AnkiConnect URL not configured")
    anki_url = anki_settings.anki_connect_url

    # Gather words
    learning = await _anki_repo.get_learning_words(session, current_user.id, body.language_id)
    pending = await _anki_repo.get_pending_words(session, current_user.id, body.language_id)
    seen_ids = {w.id for w in pending}
    all_words = list(pending) + [w for w in learning if w.id not in seen_ids]

    if not all_words:
        return AnkiSyncResponse(synced=0, queued=0, pending_total=0)

    # Resolve language
    lang_row = await session.get(Language, body.language_id)
    lang_name = lang_row.name if lang_row else str(body.language_id)
    lang_code = lang_row.code if lang_row else ""
    deck_name = f"{current_user.username}::{lang_name}"

    try:
        # Ensure Slovo model exists in Anki
        await ensure_slovo_model(anki_url)

        # Batch-fetch enrichment data
        lemmas = [w.word for w in all_words]
        definitions = await _dict_repo.batch_lookup(session, lemmas, lang_code, "en")
        freq_tiers = await _freq_repo.batch_lookup(session, lang_code, lemmas)

        # Build notes with all 10 fields + clip audio where available
        app_settings = get_settings()
        notes = []
        for w in all_words:
            audio_field = ""

            # Try to clip audio for this word
            if w.source_page_id and w.source_sentence_index is not None and ffmpeg_available():
                alignment = await _audio_repo.get_alignment_for_sentence(
                    session, w.source_page_id, w.source_sentence_index
                )
                if alignment and alignment.get("audio_file"):
                    audio_path = os.path.join(app_settings.storage_root, alignment["audio_file"])
                    audio_bytes = clip_audio(
                        audio_path,
                        alignment["audio_start_ms"],
                        alignment["audio_end_ms"],
                    )
                    if audio_bytes:
                        filename = f"slovo_{w.id}.mp3"
                        b64 = base64.b64encode(audio_bytes).decode("ascii")
                        await store_media_file(anki_url, filename, b64)
                        audio_field = f"[sound:{filename}]"

            sentence_ctx = (w.sentence_context or "")[:500]

            notes.append({
                "deckName": deck_name,
                "modelName": SLOVO_MODEL_NAME,
                "fields": {
                    "Word": w.word,
                    "POS": w.pos or "",
                    "Gender": w.gender or "",
                    "Reading": w.reading or "",
                    "Morphology": w.feats or "",
                    "Definition": definitions.get(w.word, ""),
                    "Hint": w.hint or "",
                    "SentenceContext": sentence_ctx,
                    "FrequencyTier": freq_tiers.get(w.word, ""),
                    "Audio": audio_field,
                },
                "options": {"allowDuplicate": False, "duplicateScope": "deck"},
                "tags": ["slovo"],
            })

        word_ids = [w.id for w in all_words]

        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                anki_url,
                json={"action": "createDeck", "version": 6, "params": {"deck": deck_name}},
            )
            resp = await client.post(
                anki_url,
                json={"action": "addNotes", "version": 6, "params": {"notes": notes}},
            )
            resp.raise_for_status()

        await _anki_repo.clear_pending(session, word_ids)
        await session.commit()
        pending_total = await _anki_repo.get_pending_count(session, current_user.id, body.language_id)
        return AnkiSyncResponse(synced=len(all_words), queued=0, pending_total=pending_total)

    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        word_ids = [w.id for w in all_words]
        await _anki_repo.mark_pending(session, word_ids)
        await session.commit()
        pending_total = await _anki_repo.get_pending_count(session, current_user.id, body.language_id)
        return AnkiSyncResponse(synced=0, queued=len(all_words), pending_total=pending_total)


