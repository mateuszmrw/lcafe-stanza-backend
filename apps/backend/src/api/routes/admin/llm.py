from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_admin
from src.api.schemas.admin import ProviderResponse
from src.core.config import get_settings
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.provider_repo import ProviderRepository
from src.infrastructure.db.repositories.system_api_key_repo import SystemApiKeyRepository

router = APIRouter(prefix="/admin/llm", tags=["admin"])
_provider_repo = ProviderRepository()
_system_key_repo = SystemApiKeyRepository()

_ENV_MODEL_FALLBACKS = {
    "openai": lambda: get_settings().openai_model,
    "claude": lambda: get_settings().claude_model,
}
_ENV_KEY_FALLBACKS = {
    "openai": lambda: get_settings().openai_api_key,
    "claude": lambda: get_settings().claude_api_key,
}


class LLMProviderStatus(BaseModel):
    provider_slug: str
    provider: ProviderResponse
    key_source: str  # "database" | "env" | "none"
    model: str | None
    model_source: str  # "database" | "env"


class LLMConfigUpsertRequest(BaseModel):
    api_key: str | None = None
    model: str | None = None

    @model_validator(mode="after")
    def at_least_one(self) -> "LLMConfigUpsertRequest":
        if self.api_key is None and self.model is None:
            raise ValueError("Provide at least one of api_key or model")
        return self


@router.get("", response_model=list[LLMProviderStatus])
async def list_llm_config(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> list[LLMProviderStatus]:
    providers = await _provider_repo.list_active_by_type(session, "llm")
    result: list[LLMProviderStatus] = []

    for provider in providers:
        db_key_exists = await _system_key_repo.exists(session, provider.id)
        env_key = _ENV_KEY_FALLBACKS.get(provider.slug, lambda: None)()

        if db_key_exists:
            key_source = "database"
        elif env_key:
            key_source = "env"
        else:
            key_source = "none"

        db_model = await _system_key_repo.get_model(session, provider.id)
        env_model = _ENV_MODEL_FALLBACKS.get(provider.slug, lambda: None)()
        model = db_model or env_model
        model_source = "database" if db_model else "env"

        result.append(LLMProviderStatus(
            provider_slug=provider.slug,
            provider=ProviderResponse.model_validate(provider),
            key_source=key_source,
            model=model,
            model_source=model_source,
        ))

    return result


@router.put("/{provider_slug}", status_code=204)
async def set_llm_config(
    provider_slug: str,
    body: LLMConfigUpsertRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    provider = await _provider_repo.find_by_slug(session, provider_slug, type_filter="llm")
    if not provider:
        raise HTTPException(status_code=404, detail="LLM provider not found")

    if body.api_key is not None:
        await _system_key_repo.upsert(
            session, provider.id, body.api_key.strip(), model=body.model
        )
    elif body.model is not None:
        updated = await _system_key_repo.update_model(session, provider.id, body.model)
        if not updated:
            raise HTTPException(
                status_code=400,
                detail="No API key stored for this provider. Set the API key first.",
            )

    await session.commit()


@router.delete("/{provider_slug}", status_code=204)
async def delete_llm_config(
    provider_slug: str,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    provider = await _provider_repo.find_by_slug(session, provider_slug, type_filter="llm")
    if not provider:
        raise HTTPException(status_code=404, detail="LLM provider not found")

    await _system_key_repo.delete(session, provider.id)
    await session.commit()
