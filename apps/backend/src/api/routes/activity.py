from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.activity_repo import DailyActivityRepository

router = APIRouter(prefix="/activity", tags=["activity"])
_repo = DailyActivityRepository()


class RecordActivityRequest(BaseModel):
    language_id: int


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int


class CalendarEntry(BaseModel):
    date: str
    pages: int


@router.post("/record", status_code=204)
async def record_activity(
    body: RecordActivityRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Record a page read for today."""
    await _repo.record_page(
        session,
        user_id=current_user.id,
        language_id=body.language_id,
        today=date.today(),
    )
    await session.commit()


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    language_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> StreakResponse:
    current, longest = await _repo.get_streak(
        session,
        user_id=current_user.id,
        language_id=language_id,
    )
    return StreakResponse(current_streak=current, longest_streak=longest)


@router.get("/calendar", response_model=list[CalendarEntry])
async def get_calendar(
    language_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CalendarEntry]:
    """Return daily page counts for the past year."""
    entries = await _repo.get_calendar(
        session,
        user_id=current_user.id,
        language_id=language_id,
    )
    return [CalendarEntry(**e) for e in entries]
