import csv
import io
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.api.schemas.vocabulary import BulkStatusUpdate, VocabularyStatusUpdate, VocabularyUpsertRequest, WordListResponse, WordResponse
from src.domain.stats.cache import invalidate_stats_cache
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.anki_repo import AnkiRepository
from src.infrastructure.db.repositories.word_repo import WordRepository

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])
_word_repo = WordRepository()
_anki_repo = AnkiRepository()


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
    return WordResponse.model_validate(updated)


@router.post("/sync-anki", response_model=AnkiSyncResponse)
async def sync_to_anki(
    body: AnkiSyncRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnkiSyncResponse:
    """Sync learning vocabulary to Anki via AnkiConnect.

    Tries to push all 'learning' words plus any previously queued words.
    If AnkiConnect is unreachable, marks words as pending for later retry.
    """
    settings = await _anki_repo.get_settings(session)
    if not settings.anki_connect_url:
        raise HTTPException(status_code=424, detail="AnkiConnect URL not configured")

    # Gather: new learning words + previously pending words
    learning = await _anki_repo.get_learning_words(session, current_user.id, body.language_id)
    pending = await _anki_repo.get_pending_words(session, current_user.id, body.language_id)

    # De-duplicate (pending words may already be in learning)
    seen_ids = {w.id for w in pending}
    all_words = list(pending) + [w for w in learning if w.id not in seen_ids]

    if not all_words:
        return AnkiSyncResponse(synced=0, queued=0, pending_total=0)

    deck_name = f"{current_user.username}/{body.language_id}"

    def _make_back(w: object) -> str:
        parts = [getattr(w, "hint", None) or getattr(w, "lemma", None) or getattr(w, "word", "")]
        ctx = getattr(w, "sentence_context", None)
        if ctx:
            parts.append(f"\n\n<i>{ctx}</i>")
        return "".join(parts)

    notes = [
        {
            "deckName": deck_name,
            "modelName": "Basic",
            "fields": {
                "Front": w.word,
                "Back": _make_back(w),
            },
            "options": {"allowDuplicate": False, "duplicateScope": "deck"},
            "tags": ["slovo"],
        }
        for w in all_words
    ]

    word_ids = [w.id for w in all_words]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Ensure deck exists
            await client.post(
                settings.anki_connect_url,
                json={"action": "createDeck", "version": 6, "params": {"deck": deck_name}},
            )
            resp = await client.post(
                settings.anki_connect_url,
                json={"action": "addNotes", "version": 6, "params": {"notes": notes}},
            )
            resp.raise_for_status()

        # Clear pending flag for all successfully synced words
        await _anki_repo.clear_pending(session, word_ids)
        await session.commit()
        pending_total = await _anki_repo.get_pending_count(session, current_user.id, body.language_id)
        return AnkiSyncResponse(synced=len(all_words), queued=0, pending_total=pending_total)

    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        # AnkiConnect unreachable or returned an error — queue for later retry
        await _anki_repo.mark_pending(session, word_ids)
        await session.commit()
        pending_total = await _anki_repo.get_pending_count(session, current_user.id, body.language_id)
        return AnkiSyncResponse(synced=0, queued=len(all_words), pending_total=pending_total)


@router.get("/anki-status", response_model=AnkiSyncResponse)
async def anki_status(
    language_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnkiSyncResponse:
    """Return current pending Anki sync count for this user+language."""
    pending_total = await _anki_repo.get_pending_count(session, current_user.id, language_id)
    return AnkiSyncResponse(synced=0, queued=0, pending_total=pending_total)
