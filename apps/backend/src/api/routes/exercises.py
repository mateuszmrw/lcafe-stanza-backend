"""API routes for reading exercises."""
import logging
import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.api.schemas.exercises import (
    ExerciseCheckResponse,
    ExerciseCompleteRequest,
    ExerciseCompleteResponse,
    ExerciseSessionResponse,
    ExerciseSnoozeRequest,
    ExerciseSnoozeResponse,
)
from src.domain.exercises.service import ExerciseService
from src.infrastructure.db.models.users import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["exercises"])
_service = ExerciseService()


@router.get("/{content_id}/exercises/check", response_model=ExerciseCheckResponse)
async def check_exercises(
    content_id: str,
    page: int = Query(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ExerciseCheckResponse:
    """Check if exercise prompt should be shown.

    Query params:
    - page: current page number (required)

    Returns whether to show the exercise prompt and how many candidate words are available.
    """
    # Verify content_id belongs to current user
    try:
        content_uuid = uuid.UUID(content_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Content item not found.")

    result = await session.execute(
        sa.text("SELECT user_id FROM content_items WHERE id = :id"),
        {"id": content_uuid},
    )
    row = result.first()
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Content item not found.")

    # Check exercises
    should_show, candidate_count = await _service.should_show(
        session,
        redis,
        current_user.id,
        content_uuid,
        current_page=page,
        is_end_of_content=False,
    )

    return ExerciseCheckResponse(should_show=should_show, candidate_count=candidate_count)


@router.get("/{content_id}/exercises", response_model=ExerciseSessionResponse)
async def generate_exercises(
    content_id: str,
    mode: str = Query("inline", regex="^(inline|practice)$"),
    page: int = Query(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ExerciseSessionResponse:
    """Generate exercise session.

    Query params:
    - mode: "inline" (since last exercise) or "practice" (all new/learning words)
    - page: current page number

    Returns session_id and up to 8 exercises.
    """
    # Verify content_id belongs to current user
    try:
        content_uuid = uuid.UUID(content_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Content item not found.")

    result = await session.execute(
        sa.text("SELECT user_id FROM content_items WHERE id = :id"),
        {"id": content_uuid},
    )
    row = result.first()
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Content item not found.")

    # Generate session
    session_result = await _service.generate_session(
        session,
        redis,
        current_user.id,
        content_uuid,
        current_page=page,
        mode=mode,
    )

    return ExerciseSessionResponse(
        session_id=session_result["session_id"],
        exercises=session_result["exercises"],
    )


@router.post("/{content_id}/exercises/complete", response_model=ExerciseCompleteResponse)
async def complete_exercises(
    content_id: str,
    body: ExerciseCompleteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ExerciseCompleteResponse:
    """Submit exercise answers and process results.

    Body:
    - session_id: exercise session ID
    - page: current page number
    - answers: list of exercise answers

    Returns exercise results and word status upgrades.
    """
    # Verify content_id belongs to current user
    try:
        content_uuid = uuid.UUID(content_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Content item not found.")

    result = await session.execute(
        sa.text("SELECT user_id FROM content_items WHERE id = :id"),
        {"id": content_uuid},
    )
    row = result.first()
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Content item not found.")

    # Complete session
    complete_result = await _service.complete_session(
        session,
        redis,
        current_user.id,
        content_uuid,
        session_id=body.session_id,
        answers=[a.model_dump() for a in body.answers],
        page=body.page,
    )

    # If session not found, return 404
    if not complete_result["results"]:
        # This could mean session expired or session_id was invalid
        # Check if there were any answers provided
        if body.answers:
            raise HTTPException(status_code=404, detail="Session not found or expired.")

    await session.commit()

    return ExerciseCompleteResponse(
        results=[
            {
                "exercise_id": r["exercise_id"],
                "correct": r["correct"],
                "correct_form": r["correct_form"],
            }
            for r in complete_result["results"]
        ],
        upgrades=[
            {
                "word_id": u["word_id"],
                "lemma": u["lemma"],
                "old_status": u["old_status"],
                "new_status": u["new_status"],
            }
            for u in complete_result["upgrades"]
        ],
    )


@router.post("/{content_id}/exercises/snooze", response_model=ExerciseSnoozeResponse)
async def snooze_exercises(
    content_id: str,
    body: ExerciseSnoozeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExerciseSnoozeResponse:
    """Snooze exercise prompt for N pages.

    Body:
    - page: current page number

    Returns the page number where the snooze expires.
    """
    # Verify content_id belongs to current user
    try:
        content_uuid = uuid.UUID(content_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Content item not found.")

    result = await session.execute(
        sa.text("SELECT user_id FROM content_items WHERE id = :id"),
        {"id": content_uuid},
    )
    row = result.first()
    if not row or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Content item not found.")

    # Snooze
    snooze_until_page = await _service.snooze(
        session,
        current_user.id,
        content_uuid,
        current_page=body.page,
    )

    await session.commit()

    return ExerciseSnoozeResponse(snooze_until_page=snooze_until_page)
