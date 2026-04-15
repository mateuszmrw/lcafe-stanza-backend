import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.core.config import get_settings
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.provider_repo import ProviderRepository
from src.infrastructure.db.repositories.system_api_key_repo import SystemApiKeyRepository
from src.infrastructure.llm.claude_client import ClaudeClient
from src.infrastructure.llm.client import LLMClient
from src.infrastructure.llm.openai_client import OpenAIClient

log = logging.getLogger(__name__)

router = APIRouter(prefix="/synonyms", tags=["synonyms"])
_provider_repo = ProviderRepository()
_system_key_repo = SystemApiKeyRepository()

_RATE_LIMIT = 10
_RATE_WINDOW = 60  # seconds


class SynonymNuanceRequest(BaseModel):
    language_id: int
    language_code: str
    word: str
    pos: str
    lemma: str
    context_sentence: str | None = None


class SynonymEntry(BaseModel):
    word: str
    register: str
    nuance: str
    example: str | None = None


class SynonymNuanceResponse(BaseModel):
    synonyms: list[SynonymEntry]
    native_language_code: str


async def _resolve_llm_client(session: AsyncSession) -> LLMClient:
    settings = get_settings()

    for slug, env_key, env_model, make_client in [
        (
            "openai",
            settings.openai_api_key,
            settings.openai_model,
            lambda key, model: OpenAIClient(api_key=key, model=model),
        ),
        (
            "claude",
            settings.claude_api_key,
            settings.claude_model,
            lambda key, model: ClaudeClient(api_key=key, model=model),
        ),
    ]:
        provider = await _provider_repo.find_by_slug(session, slug)
        key: str | None = None
        model: str = env_model
        if provider:
            key = await _system_key_repo.get_decrypted(session, provider.id)
            db_model = await _system_key_repo.get_model(session, provider.id)
            if db_model:
                model = db_model
        if not key:
            key = env_key
        if key:
            return make_client(key, model)  # type: ignore[operator]

    raise HTTPException(
        status_code=503,
        detail="No LLM provider configured.",
    )


async def _check_rate_limit(redis: Redis, user_id: str) -> None:
    key = f"synonyms:user:{user_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _RATE_WINDOW)
    if count > _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {_RATE_LIMIT} synonym requests per minute.",
        )


_SYSTEM_PROMPT = """\
You are a vocabulary coach helping a language learner understand synonym nuances.
Given a word, find 2-4 near-synonyms and explain the register and nuance differences.

Rules:
- Focus on practical differences: when would a native speaker choose each word?
- Include register (formal, informal, slang, literary, colloquial, neutral, technical).
- Keep nuance explanations concise (1-2 sentences).
- Optionally include a short example sentence for each synonym.
- Write explanations in the learner's native language.
- NEVER include the original word in the synonyms list.

Respond ONLY with valid JSON, no markdown fences:
{
  "synonyms": [
    {
      "word": "<synonym in target language>",
      "register": "<formal|informal|slang|literary|colloquial|neutral|technical>",
      "nuance": "<explanation in learner's native language>",
      "example": "<short example sentence in target language, or null>"
    }
  ]
}"""


@router.post("/nuance", response_model=SynonymNuanceResponse)
async def get_synonym_nuance(
    body: SynonymNuanceRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SynonymNuanceResponse:
    await _check_rate_limit(redis, str(current_user.id))

    native = current_user.native_language_code or "en"
    context_line = f"Context sentence: {body.context_sentence}" if body.context_sentence else ""
    user_prompt = (
        f"Target language: {body.language_code}\n"
        f"Word: {body.word!r} (lemma: {body.lemma!r}, POS: {body.pos})\n"
        f"{context_line}\n"
        f"Learner's native language: {native}\n"
        f"Write all nuance and register explanations in {native}."
    ).strip()

    llm = await _resolve_llm_client(session)

    try:
        raw = await llm.complete(_SYSTEM_PROMPT, user_prompt)
        data = json.loads(raw)
        return SynonymNuanceResponse(
            synonyms=[SynonymEntry(**s) for s in data["synonyms"]],
            native_language_code=native,
        )
    except Exception as exc:
        log.error("Synonym nuance failed: %s | raw=%r", exc, locals().get("raw", ""))
        raise HTTPException(status_code=502, detail="LLM returned an invalid response.")
