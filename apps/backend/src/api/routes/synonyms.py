import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.domain.rate_limit import check_rate_limit
from src.infrastructure.db.models.users import User
from src.infrastructure.llm.resolver import resolve_llm_client

log = logging.getLogger(__name__)

router = APIRouter(prefix="/synonyms", tags=["synonyms"])

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
    await check_rate_limit(redis, f"synonyms:user:{current_user.id}", _RATE_LIMIT, _RATE_WINDOW)

    native = current_user.native_language_code or "en"
    context_line = f"Context sentence: {body.context_sentence}" if body.context_sentence else ""
    user_prompt = (
        f"Target language: {body.language_code}\n"
        f"Word: {body.word!r} (lemma: {body.lemma!r}, POS: {body.pos})\n"
        f"{context_line}\n"
        f"Learner's native language: {native}\n"
        f"Write all nuance and register explanations in {native}."
    ).strip()

    llm = await resolve_llm_client(session)

    try:
        raw = await llm.complete(_SYSTEM_PROMPT, user_prompt)
        data = json.loads(raw)
        return SynonymNuanceResponse(
            synonyms=[SynonymEntry(**s) for s in data["synonyms"]],
            native_language_code=native,
        )
    except Exception:
        # Don't log the raw exception or LLM response — may contain API key material
        log.error("Synonym nuance failed (exception details suppressed)")
        raise HTTPException(status_code=502, detail="LLM returned an invalid response.")
