import os
import shutil

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.core.config import get_settings
from src.infrastructure.db.models.content import Book, ContentItem
from src.infrastructure.db.models.words import Word
from src.api.schemas.admin import ProviderResponse
from src.api.schemas.users import ActiveLanguageRequest, ApiKeyResponse, ApiKeyUpsertRequest, ProficiencyUpdateRequest, UserResponse, UserUpdateRequest, VALID_PROFICIENCY_LEVELS
from src.domain.users.models import UserUpdate
from src.domain.users.service import UserService
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.users import User, UserLanguageProfile
from src.infrastructure.db.repositories.api_key_repo import ApiKeyRepository
from src.infrastructure.db.repositories.provider_repo import ProviderRepository

router = APIRouter(prefix="/users", tags=["users"])
_user_service = UserService()
_provider_repo = ProviderRepository()
_api_key_repo = ApiKeyRepository()


async def _build_user_response(user: User, session: AsyncSession) -> UserResponse:
    """Populate UserResponse including active language fields."""
    lang = None
    profile = None
    if user.active_language_id is not None:
        lang = await session.get(Language, user.active_language_id)
        result = await session.execute(
            sa.select(UserLanguageProfile).where(
                UserLanguageProfile.user_id == user.id,
                UserLanguageProfile.language_id == user.active_language_id,
            )
        )
        profile = result.scalar_one_or_none()

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

    # Build the upsert values for this language profile
    upsert_values: dict = {
        "user_id": current_user.id,
        "language_id": current_user.active_language_id,
    }
    update_set: dict = {}

    if body.proficiency_level is not None:
        upsert_values["proficiency_level"] = body.proficiency_level
        update_set["proficiency_level"] = body.proficiency_level
    if body.native_language_code is not None:
        upsert_values["native_language_code"] = body.native_language_code
        update_set["native_language_code"] = body.native_language_code
    if body.auto_ignore_proper_nouns is not None:
        upsert_values["auto_ignore_proper_nouns"] = body.auto_ignore_proper_nouns
        update_set["auto_ignore_proper_nouns"] = body.auto_ignore_proper_nouns

    if update_set:
        await session.execute(
            sa.dialects.postgresql.insert(UserLanguageProfile)
            .values(**upsert_values)
            .on_conflict_do_update(
                index_elements=["user_id", "language_id"],
                set_=update_set,
            )
        )
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
    result = await session.execute(
        sa.select(Book.file_path, Book.audio_file_path)
        .join(ContentItem, Book.content_item_id == ContentItem.id)
        .where(ContentItem.user_id == current_user.id)
    )
    file_paths = [p for row in result for p in row if p]

    words_result = await session.execute(
        sa.delete(Word).where(Word.user_id == current_user.id)
    )
    books_result = await session.execute(
        sa.delete(ContentItem).where(ContentItem.user_id == current_user.id)
    )
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
        deleted_books=books_result.rowcount,
        deleted_words=words_result.rowcount,
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
