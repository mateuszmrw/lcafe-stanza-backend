from __future__ import annotations

import random
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.drills import DrillQuestion, DrillSessionResponse
from src.domain.grammar.drill_service import _CASE_BY_LANG, lang_lookup
from src.domain.grammar.preposition_rules import (
    SUPPORTED_PREPOSITION_LANGUAGES,
    get_case_options,
    get_rules,
)
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.language_repo import LanguageRepository

_PREP_PROMPT_PREFIX: dict[str, str] = {
    "pl": "Jaki przypadek następuje po",
    "ru": "Какой падеж после",
    "de": "Welcher Fall folgt nach",
    "cs": "Jaký pád následuje po",
    "_default": "Which case follows",
}


class PrepositionCaseService:
    def __init__(self) -> None:
        self._lang_repo = LanguageRepository()

    async def generate_session(
        self,
        user_id: uuid.UUID,
        active_language_id: int,
        session_size: int,
        db: AsyncSession,
    ) -> DrillSessionResponse:
        language = await self._lang_repo.find_by_id(db, active_language_id)
        if not language:
            return DrillSessionResponse(session_id="", available=False, reason="no_active_language")

        lang_code = language.code
        if lang_code not in SUPPORTED_PREPOSITION_LANGUAGES:
            return DrillSessionResponse(session_id="", available=False, reason="no_form_data")

        rules = get_rules(lang_code)
        if not rules:
            return DrillSessionResponse(session_id="", available=False, reason="no_form_data")

        # Requires at least some learning words (same gate as other drills)
        has_learning = await db.scalar(
            sa.select(sa.func.count())
            .select_from(Word)
            .where(
                Word.user_id == user_id,
                Word.language_id == active_language_id,
                Word.status == "learning",
                Word.skip_in_vocabulary == False,  # noqa: E712
            )
        )
        if not has_learning:
            return DrillSessionResponse(session_id="", available=False, reason="no_learning_words")

        case_map = lang_lookup(_CASE_BY_LANG, lang_code)
        case_options_raw = get_case_options(lang_code)
        all_case_display = [case_map.get(c, c.capitalize()) for c in case_options_raw]

        prompt_prefix = _PREP_PROMPT_PREFIX.get(lang_code) or _PREP_PROMPT_PREFIX["_default"]

        pool = list(rules)
        random.shuffle(pool)
        pool = pool[:session_size]

        questions: list[DrillQuestion] = []
        for preposition, case_tag, hint in pool:
            correct_display = case_map.get(case_tag, case_tag.capitalize())
            prompt = f"{prompt_prefix} «{preposition}»"
            if hint:
                prompt += f" ({hint})"
            prompt += "?"

            options = list(all_case_display)
            random.shuffle(options)

            questions.append(
                DrillQuestion(
                    id=str(uuid.uuid4()),
                    type="multiple_choice",
                    lemma=preposition,
                    display_lemma=preposition,
                    prompt=prompt,
                    form_type=f"«{preposition}» + {correct_display}",
                    options=options,
                    correct_form=correct_display,
                    accepted_forms=[correct_display],
                )
            )

        if not questions:
            return DrillSessionResponse(session_id="", available=False, reason="no_drillable_words")

        return DrillSessionResponse(
            session_id=str(uuid.uuid4()),
            available=True,
            questions=questions,
            drill_type="preposition_case",
        )
