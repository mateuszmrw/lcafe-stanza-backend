import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas.admin import ProviderResponse
from src.api.schemas.users import ActiveLanguageRequest, ApiKeyResponse, ApiKeyUpsertRequest, ProficiencyUpdateRequest, UserResponse, UserUpdateRequest, VALID_PROFICIENCY_LEVELS
from src.core.config import get_settings
from src.domain.users.models import UserUpdate
from src.domain.users.service import UserService
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.api_key_repo import ApiKeyRepository
from src.infrastructure.db.repositories.content_repo import ContentRepository
from src.infrastructure.db.repositories.provider_repo import ProviderRepository
from src.infrastructure.db.repositories.user_language_profile_repo import UserLanguageProfileRepository
from src.infrastructure.db.repositories.word_repo import WordRepository

router = APIRouter(prefix="/users", tags=["users"])
_user_service = UserService()
_provider_repo = ProviderRepository()
_api_key_repo = ApiKeyRepository()
_lang_profile_repo = UserLanguageProfileRepository()
_content_repo = ContentRepository()
_word_repo = WordRepository()


async def _build_user_response(user: User, session: AsyncSession) -> UserResponse:
    """Populate UserResponse including active language fields."""
    lang = None
    profile = None
    if user.active_language_id is not None:
        lang = await session.get(Language, user.active_language_id)
        profile = await _lang_profile_repo.find_by_user_and_language(
            session, user.id, user.active_language_id
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        active_language_id=user.active_language_id,
        active_language_code=lang.code if lang else None,
        active_language_name=lang.name if lang else None,
        proficiency_level=profile.proficiency_level if profile else None,
        # Per-language values; fall back to global user values when not set
        native_language_code=(
            profile.native_language_code
            if profile and profile.native_language_code is not None
            else user.native_language_code
        ),
        auto_ignore_proper_nouns=(
            profile.auto_ignore_proper_nouns
            if profile and profile.auto_ignore_proper_nouns is not None
            else user.auto_ignore_proper_nouns
        ),
    )


@router.get("/me/providers", response_model=list[ProviderResponse])
async def list_my_providers(
    type: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ProviderResponse]:
    """List active providers visible to the current user (for API key management)."""
    providers = await _provider_repo.list_all(session, type_filter=type)
    return [ProviderResponse.model_validate(p) for p in providers if p.is_active]


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await _build_user_response(current_user, session)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    updated = await _user_service.update(
        session, current_user.id, UserUpdate(**body.model_dump())
    )
    await session.commit()
    return await _build_user_response(updated, session)


@router.patch("/me/active-language", response_model=UserResponse)
async def set_active_language(
    body: ActiveLanguageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    language = await session.get(Language, body.language_id)
    if not language or not language.is_active:
        raise HTTPException(status_code=404, detail="Language not found or inactive")
    current_user.active_language_id = body.language_id
    await session.commit()
    return await _build_user_response(current_user, session)


@router.patch("/me/proficiency", response_model=UserResponse)
async def set_proficiency(
    body: ProficiencyUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    if body.proficiency_level is not None and body.proficiency_level not in VALID_PROFICIENCY_LEVELS:
        raise HTTPException(status_code=422, detail=f"proficiency_level must be one of {sorted(VALID_PROFICIENCY_LEVELS)}")
    if current_user.active_language_id is None:
        raise HTTPException(status_code=422, detail="Set an active language before updating learning profile.")

    fields: dict = {}
    if body.proficiency_level is not None:
        fields["proficiency_level"] = body.proficiency_level
    if body.native_language_code is not None:
        fields["native_language_code"] = body.native_language_code
    if body.auto_ignore_proper_nouns is not None:
        fields["auto_ignore_proper_nouns"] = body.auto_ignore_proper_nouns

    await _lang_profile_repo.upsert(session, current_user.id, current_user.active_language_id, **fields)
    await session.commit()
    return await _build_user_response(current_user, session)


@router.delete("/me", status_code=204)
async def delete_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    await _user_service.deactivate(session, current_user.id)
    await session.commit()


@router.get("/me/api-keys/{provider_slug}", response_model=ApiKeyResponse)
async def get_api_key(
    provider_slug: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    provider = await _provider_repo.find_by_slug(session, provider_slug)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    value = await _api_key_repo.get_decrypted(session, current_user.id, provider.id)
    return ApiKeyResponse(provider_slug=provider_slug, exists=value is not None)


@router.put("/me/api-keys/{provider_slug}", status_code=204)
async def upsert_api_key(
    provider_slug: str,
    body: ApiKeyUpsertRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    provider = await _provider_repo.find_by_slug(session, provider_slug)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    await _api_key_repo.upsert(session, current_user.id, provider.id, body.api_key.strip())
    await session.commit()


class UserDataResetRequest(BaseModel):
    confirmation: str


class UserDataResetResponse(BaseModel):
    deleted_books: int
    deleted_words: int


@router.delete("/me/data", response_model=UserDataResetResponse)
async def reset_my_data(
    body: UserDataResetRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserDataResetResponse:
    """Delete all books, pages, and vocabulary for the current user. Irreversible."""
    if body.confirmation != "DELETE ALL DATA":
        raise HTTPException(
            status_code=422,
            detail="Confirmation phrase must be exactly: DELETE ALL DATA",
        )

    # Collect file paths before deletion so we can clean up disk afterwards.
    file_paths = await _content_repo.list_book_file_paths_for_user(
        session, current_user.id
    )

    deleted_words = await _word_repo.delete_all_for_user(session, current_user.id)
    deleted_books = await _content_repo.delete_all_for_user(session, current_user.id)
    await session.commit()

    settings = get_settings()
    for rel_path in file_paths:
        abs_path = os.path.join(settings.storage_root, rel_path)
        if os.path.isfile(abs_path):
            try:
                os.remove(abs_path)
            except OSError:
                pass

    return UserDataResetResponse(
        deleted_books=deleted_books,
        deleted_words=deleted_words,
    )


@router.delete("/me/api-keys/{provider_slug}", status_code=204)
async def delete_api_key(
    provider_slug: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    provider = await _provider_repo.find_by_slug(session, provider_slug)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    await _api_key_repo.delete(session, current_user.id, provider.id)
    await session.commit()
