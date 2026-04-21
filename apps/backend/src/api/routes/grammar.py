import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, get_redis
from src.api.schemas.drills import (
    AvailableDrill,
    AvailableDrillsResponse,
    DrillResult,
    DrillSessionResponse,
    DrillSubmitRequest,
    DrillSubmitResponse,
)
from src.api.schemas.grammar import GrammarExplainRequest, GrammarExplainResponse
from src.domain.grammar.aspect_pair_service import AspectPairService
from src.domain.grammar.case_identification_service import CaseIdentificationService
from src.domain.grammar.drill_service import DrillSessionService, normalize_answer
from src.domain.grammar.preposition_case_service import PrepositionCaseService
from src.domain.grammar.preposition_rules import (
    ASPECT_LANGUAGES,
    SUPPORTED_PREPOSITION_LANGUAGES,
    get_case_options,
)
from src.domain.grammar.service import GrammarExplanationService
from src.domain.rate_limit import check_rate_limit
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.dictionary_forms_repo import DictionaryFormsRepository
from src.infrastructure.db.repositories.grammar_drills_repo import GrammarDrillsRepository
from src.infrastructure.db.repositories.language_repo import LanguageRepository
from src.infrastructure.db.repositories.user_language_profile_repo import UserLanguageProfileRepository
from src.infrastructure.llm.resolver import resolve_llm_client

log = logging.getLogger(__name__)

router = APIRouter(prefix="/grammar", tags=["grammar"])
_lang_profile_repo = UserLanguageProfileRepository()
_language_repo = LanguageRepository()
_drills_repo = GrammarDrillsRepository()
_forms_repo = DictionaryFormsRepository()

_RATE_LIMIT = 3
_RATE_WINDOW = 60  # seconds

_DRILL_META = {
    "form_production": {
        "name": "Form Production",
        "description": "Inflect words into the correct grammatical form.",
    },
    "case_identification": {
        "name": "Case Recognition",
        "description": "Identify what case a word is in from a real sentence.",
    },
    "preposition_case": {
        "name": "Preposition + Case",
        "description": "Match each preposition to the case it governs.",
    },
    "aspect_pairs": {
        "name": "Aspect Pairs",
        "description": "Give the perfective or imperfective counterpart of a verb.",
    },
}


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
    except ValueError as exc:
        # ValueError is raised by the service when the LLM returns unparseable JSON
        # (it already logged the raw response). Exception type only — no exc details
        # in case the message ever contains SDK internals.
        log.warning("Grammar explanation returned unparseable LLM response: %s", exc)
        raise HTTPException(status_code=502, detail="LLM returned an invalid response. Try again.")


@router.get("/drills/available", response_model=AvailableDrillsResponse)
async def get_available_drills(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AvailableDrillsResponse:
    if current_user.active_language_id is None:
        drills = [
            AvailableDrill(type=t, available=False, reason="no_active_language", **_DRILL_META[t])
            for t in _DRILL_META
        ]
        return AvailableDrillsResponse(drills=drills)

    lang = await _language_repo.find_by_id(session, current_user.active_language_id)
    lang_code = lang.code if lang else ""

    has_forms = await _forms_repo.has_forms_for_language(session, lang_code)
    case_opts = get_case_options(lang_code)

    drills: list[AvailableDrill] = [
        AvailableDrill(
            type="form_production",
            available=has_forms,
            reason=None if has_forms else "no_form_data",
            **_DRILL_META["form_production"],
        ),
        AvailableDrill(
            type="case_identification",
            available=len(case_opts) >= 3,
            reason=None if len(case_opts) >= 3 else "no_form_data",
            **_DRILL_META["case_identification"],
        ),
        AvailableDrill(
            type="preposition_case",
            available=lang_code in SUPPORTED_PREPOSITION_LANGUAGES,
            reason=None if lang_code in SUPPORTED_PREPOSITION_LANGUAGES else "no_form_data",
            **_DRILL_META["preposition_case"],
        ),
        AvailableDrill(
            type="aspect_pairs",
            available=lang_code in ASPECT_LANGUAGES and has_forms,
            reason=None if (lang_code in ASPECT_LANGUAGES and has_forms) else "no_form_data",
            **_DRILL_META["aspect_pairs"],
        ),
    ]
    return AvailableDrillsResponse(drills=drills)


@router.get("/drills", response_model=DrillSessionResponse)
async def get_grammar_drills(
    session_size: int = Query(default=15, ge=1, le=20),
    drill_type: str = Query(default="form_production"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> DrillSessionResponse:
    if current_user.active_language_id is None:
        return DrillSessionResponse(
            session_id="", available=False, reason="no_active_language"
        )

    if drill_type == "case_identification":
        service: DrillSessionService | CaseIdentificationService | PrepositionCaseService | AspectPairService = CaseIdentificationService()
    elif drill_type == "preposition_case":
        service = PrepositionCaseService()
    elif drill_type == "aspect_pairs":
        service = AspectPairService()
    else:
        service = DrillSessionService()

    result = await service.generate_session(
        user_id=current_user.id,
        active_language_id=current_user.active_language_id,
        session_size=session_size,
        db=session,
    )

    if result.available and result.questions:
        await _drills_repo.store_session(
            redis,
            result.session_id,
            [q.model_dump() for q in result.questions],
        )

    return result


@router.post("/drills/submit", response_model=DrillSubmitResponse)
async def submit_grammar_drills(
    body: DrillSubmitRequest,
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
) -> DrillSubmitResponse:
    session_data = await _drills_repo.get_session(redis, body.session_id)
    if session_data is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    results: list[DrillResult] = []
    score = 0

    for ans in body.answers:
        qdata = session_data.get(ans.question_id)
        if not qdata:
            continue

        accepted = qdata.get("accepted_forms", [qdata["correct_form"]])
        user_norm = normalize_answer(ans.answer)
        is_correct = any(normalize_answer(f) == user_norm for f in accepted)

        if is_correct:
            score += 1

        results.append(
            DrillResult(
                question_id=ans.question_id,
                correct=is_correct,
                user_answer=ans.answer,
                correct_form=qdata["correct_form"],
                lemma=qdata.get("lemma", ""),
                form_type=qdata.get("form_type", ""),
            )
        )

    return DrillSubmitResponse(score=score, total=len(results), results=results)
