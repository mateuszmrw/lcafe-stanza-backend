from __future__ import annotations

import random
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.drills import DrillQuestion, DrillSessionResponse
from src.domain.grammar.drill_service import _CASE_BY_LANG, reconstruct_sentence_plain
from src.domain.grammar.drill_service import lang_lookup
from src.domain.grammar.preposition_rules import get_case_options
from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.language_repo import LanguageRepository

_STANZA_CASE_MAP: dict[str, str] = {
    "Nom": "nominative",
    "Gen": "genitive",
    "Dat": "dative",
    "Acc": "accusative",
    "Ins": "instrumental",
    "Loc": "locative",
    "Voc": "vocative",
    "Prep": "prepositional",
    "Abl": "ablative",
}

_CASE_ID_PROMPT: dict[str, str] = {
    "pl": "W jakim przypadku jest wyróżnione słowo?",
    "ru": "В каком падеже стоит выделенное слово?",
    "de": "In welchem Fall steht das markierte Wort?",
    "cs": "V jakém pádu je zvýrazněné slovo?",
    "_default": "What case is the highlighted word in?",
}

# Scan at most this many pages per session; keeps the single batch query bounded.
_MAX_PAGES_TO_SCAN = 300


def _parse_case(feats: str | None) -> str | None:
    if not feats:
        return None
    for part in feats.split("|"):
        if part.startswith("Case="):
            return _STANZA_CASE_MAP.get(part[5:])
    return None


class CaseIdentificationService:
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
        case_options_raw = get_case_options(lang_code)
        if len(case_options_raw) < 3:
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

        learning_lemmas: set[str] = {(row.lemma or row.word) for row in learning}
        case_map = lang_lookup(_CASE_BY_LANG, lang_code)
        all_case_display = [case_map.get(c, c.capitalize()) for c in case_options_raw]
        prompt = _CASE_ID_PROMPT.get(lang_code) or _CASE_ID_PROMPT["_default"]

        # Single batch query instead of one query per learning word.
        page_result = await db.execute(
            sa.select(ContentPage.tokens)
            .join(ContentItem, ContentPage.content_item_id == ContentItem.id)
            .where(
                ContentItem.user_id == user_id,
                ContentPage.tokens.is_not(None),
            )
            .limit(_MAX_PAGES_TO_SCAN)
        )
        all_page_tokens: list[list[dict]] = page_result.scalars().all()

        # Collect (lemma, tok, case_tag, sentence) candidates from all fetched pages.
        candidates: list[tuple[str, dict, str, str]] = []
        for tokens in all_page_tokens:
            for tok in tokens:
                lemma = tok.get("l")
                if lemma not in learning_lemmas:
                    continue
                feats = tok.get("feats") or tok.get("f") or ""
                case_tag = _parse_case(feats)
                if not case_tag or case_tag not in case_options_raw:
                    continue
                si = tok.get("si")
                if si is None:
                    continue
                sentence = reconstruct_sentence_plain(tokens, si)
                if not sentence:
                    continue
                candidates.append((lemma, tok, case_tag, sentence))

        if not candidates:
            return DrillSessionResponse(session_id="", available=False, reason="no_drillable_words")

        random.shuffle(candidates)
        questions: list[DrillQuestion] = []
        seen: set[str] = set()

        for lemma, tok, case_tag, sentence in candidates:
            if len(questions) >= session_size:
                break
            if lemma in seen:
                continue

            surface = tok.get("w", lemma)
            correct_display = case_map.get(case_tag, case_tag.capitalize())
            options = list(all_case_display)
            random.shuffle(options)

            questions.append(
                DrillQuestion(
                    id=str(uuid.uuid4()),
                    type="case_identification",
                    lemma=lemma,
                    display_lemma=surface,
                    prompt=prompt,
                    form_type=correct_display,
                    sentence=sentence,
                    highlighted_word=surface,
                    options=options,
                    correct_form=correct_display,
                    accepted_forms=[correct_display],
                )
            )
            seen.add(lemma)

        if not questions:
            return DrillSessionResponse(session_id="", available=False, reason="no_drillable_words")

        return DrillSessionResponse(
            session_id=str(uuid.uuid4()),
            available=True,
            questions=questions,
            drill_type="case_identification",
        )
