from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.infrastructure.db.repositories.language_repo import LanguageRepository

router = APIRouter(prefix="/languages", tags=["languages"])
_lang_repo = LanguageRepository()


class LanguageItem(BaseModel):
    id: int
    code: str
    name: str
    flag_emoji: str | None
    reader_config: dict = {}


@router.get("", response_model=list[LanguageItem])
async def list_languages(
    session: AsyncSession = Depends(get_db),
) -> list[LanguageItem]:
    languages = await _lang_repo.list_all(session)
    return [
        LanguageItem(
            id=lang.id,
            code=lang.code,
            name=lang.name,
            flag_emoji=lang.flag_emoji,
            reader_config=lang.reader_config,
        )
        for lang in languages
        if lang.is_active
    ]
