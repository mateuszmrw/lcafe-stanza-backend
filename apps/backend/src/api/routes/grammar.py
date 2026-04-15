import logging

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.api.schemas.grammar import GrammarExplainRequest, GrammarExplainResponse
from src.domain.grammar.service import GrammarExplanationService
from src.domain.rate_limit import check_rate_limit
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.user_language_profile_repo import UserLanguageProfileRepository
from src.infrastructure.llm.resolver import resolve_llm_client

log = logging.getLogger(__name__)

router = APIRouter(prefix="/grammar", tags=["grammar"])
_lang_profile_repo = UserLanguageProfileRepository()

_RATE_LIMIT = 3
_RATE_WINDOW = 60  # seconds


@router.post("/explain", response_model=GrammarExplainResponse)
async def explain_grammar(
    body: GrammarExplainRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> GrammarExplainResponse:
    if not body.tokens:
        raise HTTPException(status_code=422, detail="tokens must not be empty")

    if current_user.active_language_id is None:
        raise HTTPException(
            status_code=400,
            detail="Please set your proficiency level first (PATCH /users/me/proficiency).",
        )

    lang_profile = await _lang_profile_repo.find_by_user_and_language(
        session, current_user.id, current_user.active_language_id
    )

    if not lang_profile or not lang_profile.proficiency_level:
        raise HTTPException(
            status_code=400,
            detail="Please set your proficiency level first (PATCH /users/me/proficiency).",
        )

    await check_rate_limit(redis, f"grammar:user:{current_user.id}", _RATE_LIMIT, _RATE_WINDOW)

    llm = await resolve_llm_client(session)
    service = GrammarExplanationService(llm)

    try:
        return await service.explain(
            tokens=body.tokens,
            language_code=body.language_code,
            proficiency_level=lang_profile.proficiency_level,
            native_language_code=current_user.native_language_code or "en",
            register=body.register,
        )
    except ValueError:
        # Don't log the raw exception — it may contain API key material from SDK internals
        log.error("Grammar explanation failed (exception details suppressed)")
        raise HTTPException(status_code=502, detail="LLM returned an invalid response. Try again.")
