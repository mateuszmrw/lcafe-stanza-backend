from __future__ import annotations

import random
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.drills import DrillQuestion, DrillSessionResponse
from src.domain.grammar.preposition_rules import ASPECT_LANGUAGES
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.dictionary_forms_repo import DictionaryFormsRepository
from src.infrastructure.db.repositories.language_repo import LanguageRepository

_ASPECT_PROMPTS: dict[str, dict[str, str]] = {
    "pl": {
        "perfective": "Forma dokonana od",
        "imperfective": "Forma niedokonana od",
    },
    "ru": {
        "perfective": "Совершенный вид от",
        "imperfective": "Несовершенный вид от",
    },
    "cs": {
        "perfective": "Dokonavý vid od",
        "imperfective": "Nedokonavý vid od",
    },
    "_default": {
        "perfective": "Perfective form of",
        "imperfective": "Imperfective form of",
    },
}

_ASPECT_FORM_TYPE: dict[str, dict[str, str]] = {
    "pl": {"perfective": "Aspekt dokonany", "imperfective": "Aspekt niedokonany"},
    "ru": {"perfective": "Совершенный вид", "imperfective": "Несовершенный вид"},
    "cs": {"perfective": "Dokonavý vid", "imperfective": "Nedokonavý vid"},
    "_default": {"perfective": "Perfective aspect", "imperfective": "Imperfective aspect"},
}


def _get_prompt(lang_code: str, aspect: str) -> str:
    lang = _ASPECT_PROMPTS.get(lang_code) or _ASPECT_PROMPTS["_default"]
    return lang.get(aspect, aspect)


def _get_form_type(lang_code: str, aspect: str) -> str:
    lang = _ASPECT_FORM_TYPE.get(lang_code) or _ASPECT_FORM_TYPE["_default"]
    return lang.get(aspect, aspect)


class AspectPairService:
    def __init__(self) -> None:
        self._forms_repo = DictionaryFormsRepository()
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
        if lang_code not in ASPECT_LANGUAGES:
            return DrillSessionResponse(session_id="", available=False, reason="no_form_data")

        rows = await db.execute(
            sa.select(Word.word, Word.lemma)
            .where(
                Word.user_id == user_id,
                Word.language_id == active_language_id,
                Word.status == "learning",
                Word.skip_in_vocabulary == False,  # noqa: E712
            )
        )
        learning = rows.all()
        if not learning:
            return DrillSessionResponse(session_id="", available=False, reason="no_learning_words")

        shuffled = list(learning)
        random.shuffle(shuffled)

        questions: list[DrillQuestion] = []
        seen: set[str] = set()

        for row in shuffled:
            if len(questions) >= session_size:
                break
            lemma = row.lemma or row.word
            if lemma in seen:
                continue
            q = await self._build_question(lemma, lang_code, db)
            if q:
                questions.append(q)
                seen.add(lemma)

        if not questions:
            return DrillSessionResponse(session_id="", available=False, reason="no_drillable_words")

        return DrillSessionResponse(
            session_id=str(uuid.uuid4()),
            available=True,
            questions=questions,
            drill_type="aspect_pairs",
        )

    async def _build_question(
        self, lemma: str, lang_code: str, db: AsyncSession
    ) -> DrillQuestion | None:
        forms = await self._forms_repo.get_forms(db, lemma, lang_code)
        aspect_forms = [
            f for f in forms
            if "perfective" in f.form_type or "imperfective" in f.form_type
        ]
        if not aspect_forms:
            return None

        target = random.choice(aspect_forms)
        # Determine which aspect we're asking for
        asked_aspect = "perfective" if "perfective" in target.form_type else "imperfective"
        correct_form = target.forms[0]

        prompt = f"{_get_prompt(lang_code, asked_aspect)} «{lemma}»:"
        form_type = _get_form_type(lang_code, asked_aspect)

        return DrillQuestion(
            id=str(uuid.uuid4()),
            type="fill_blank",
            lemma=lemma,
            display_lemma=lemma,
            prompt=prompt,
            form_type=form_type,
            correct_form=correct_form,
            accepted_forms=target.forms,
        )
