from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.api.schemas.admin import (
    LanguageCreateRequest,
    LanguageResponse,
    LanguageUpdateRequest,
    NlpConfigResponse,
    NlpConfigUpdateRequest,
)
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.language_repo import LanguageRepository

router = APIRouter(prefix="/admin/languages", tags=["admin"])
_lang_repo = LanguageRepository()


@router.get("", response_model=list[LanguageResponse])
async def list_languages(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[LanguageResponse]:
    languages = await _lang_repo.list_all(session)
    return [LanguageResponse.model_validate(lang) for lang in languages]


@router.post("", response_model=LanguageResponse, status_code=201)
async def create_language(
    body: LanguageCreateRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> LanguageResponse:
    language = await _lang_repo.create(
        session, code=body.code, name=body.name, flag_emoji=body.flag_emoji
    )
    await session.commit()
    return LanguageResponse.model_validate(language)


@router.put("/{language_id}", response_model=LanguageResponse)
async def update_language(
    language_id: int,
    body: LanguageUpdateRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> LanguageResponse:
    language = await _lang_repo.update(
        session,
        language_id,
        name=body.name,
        flag_emoji=body.flag_emoji,
        is_active=body.is_active,
    )
    if not language:
        raise HTTPException(status_code=404, detail="Language not found")
    await session.commit()
    return LanguageResponse.model_validate(language)


@router.get("/{language_id}/nlp-config", response_model=NlpConfigResponse)
async def get_nlp_config(
    language_id: int,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> NlpConfigResponse:
    config = await _lang_repo.get_nlp_config(session, language_id)
    if not config:
        raise HTTPException(status_code=404, detail="NLP config not found")
    return NlpConfigResponse.model_validate(config)


@router.put("/{language_id}/nlp-config", response_model=NlpConfigResponse)
async def set_nlp_config(
    language_id: int,
    body: NlpConfigUpdateRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> NlpConfigResponse:
    config = await _lang_repo.set_nlp_config(
        session, language_id, str(body.provider_id), body.config
    )
    await session.commit()
    return NlpConfigResponse.model_validate(config)
