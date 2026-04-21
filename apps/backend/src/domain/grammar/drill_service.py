from __future__ import annotations

import json
import random
import unicodedata
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB as PgJSONB
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.drills import DrillQuestion, DrillSessionResponse
from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.dictionary_forms_repo import (
    DictionaryFormsRepository,
    WordForm,
)
from src.infrastructure.db.repositories.language_repo import LanguageRepository

_FILL_BLANK_RATIO = 0.6

# OpenRussian compact form types → Russian-language prompts (always Russian)
_RU_COMPACT_PROMPTS: dict[str, str] = {
    "nom_sg": "Именительный — ед.ч.",
    "gen_sg": "Родительный — ед.ч.",
    "dat_sg": "Дательный — ед.ч.",
    "acc_sg": "Винительный — ед.ч.",
    "ins_sg": "Творительный — ед.ч.",
    "prep_sg": "Предложный — ед.ч.",
    "nom_pl": "Именительный — мн.ч.",
    "gen_pl": "Родительный — мн.ч.",
    "dat_pl": "Дательный — мн.ч.",
    "acc_pl": "Винительный — мн.ч.",
    "ins_pl": "Творительный — мн.ч.",
    "prep_pl": "Предложный — мн.ч.",
    "masc_short": "Краткая форма (м.р.)",
    "fem_short": "Краткая форма (ж.р.)",
    "neut_short": "Краткая форма (ср.р.)",
    "pl_short": "Краткая форма (мн.ч.)",
    "inf": "Инфинитив",
    "past_m": "Прошедшее — «он ...»",
    "past_f": "Прошедшее — «она ...»",
    "past_n": "Прошедшее — «оно ...»",
    "past_pl": "Прошедшее — «они ...»",
    "1sg": "«Я ...»",
    "2sg": "«Ты ...»",
    "3sg": "«Он / она ...»",
    "1pl": "«Мы ...»",
    "2pl": "«Вы ...»",
    "3pl": "«Они ...»",
    "imper_sg": "Повелительное — одному",
    "imper_pl": "Повелительное — группе",
}

# Case names per language (Wiktionary tag → native case name)
_CASE_BY_LANG: dict[str, dict[str, str]] = {
    "ru": {
        "nominative": "Именительный",
        "genitive": "Родительный",
        "dative": "Дательный",
        "accusative": "Винительный",
        "instrumental": "Творительный",
        "locative": "Предложный",
        "prepositional": "Предложный",
        "vocative": "Звательный",
        "ablative": "Отложительный",
    },
    "pl": {
        "nominative": "Mianownik",
        "genitive": "Dopełniacz",
        "dative": "Celownik",
        "accusative": "Biernik",
        "instrumental": "Narzędnik",
        "locative": "Miejscownik",
        "prepositional": "Miejscownik",
        "vocative": "Wołacz",
    },
    "de": {
        "nominative": "Nominativ",
        "genitive": "Genitiv",
        "dative": "Dativ",
        "accusative": "Akkusativ",
    },
    "cs": {
        "nominative": "Nominativ",
        "genitive": "Genitiv",
        "dative": "Dativ",
        "accusative": "Akuzativ",
        "instrumental": "Instrumentál",
        "locative": "Lokál",
        "vocative": "Vokativ",
    },
    "_default": {
        "nominative": "Nominative",
        "genitive": "Genitive",
        "dative": "Dative",
        "accusative": "Accusative",
        "instrumental": "Instrumental",
        "locative": "Locative",
        "prepositional": "Prepositional",
        "vocative": "Vocative",
        "ablative": "Ablative",
    },
}

# Number abbreviations per language
_NUM_BY_LANG: dict[str, dict[str, str]] = {
    "ru": {"singular": "ед.ч.", "plural": "мн.ч."},
    "pl": {"singular": "lp.", "plural": "lm."},
    "de": {"singular": "Sg.", "plural": "Pl."},
    "cs": {"singular": "j.č.", "plural": "mn.č."},
    "_default": {"singular": "sg.", "plural": "pl."},
}

# Gender/animacy abbreviations per language
_GENDER_BY_LANG: dict[str, dict[str, str]] = {
    "ru": {"masculine": "м.р.", "feminine": "ж.р.", "neuter": "ср.р."},
    "pl": {
        "masculine": "r.m.",
        "feminine": "r.ż.",
        "neuter": "r.n.",
        "virile": "r.mę.-os.",
        "non-virile": "r.niemę.",
        "non virile": "r.niemę.",
    },
    "de": {"masculine": "m.", "feminine": "f.", "neuter": "n."},
    "_default": {
        "masculine": "masc.",
        "feminine": "fem.",
        "neuter": "neut.",
        "virile": "virile",
        "non-virile": "non-vir.",
        "non virile": "non-vir.",
    },
}

# Verb mood/tense terms per language
_MOOD_BY_LANG: dict[str, dict[str, str]] = {
    "ru": {
        "conditional": "Условное",
        "imperative": "Повелительное",
        "infinitive": "Инфинитив",
        "subjunctive": "Сослагательное",
        "past": "Прошедшее",
        "present": "Настоящее",
        "future": "Будущее",
    },
    "pl": {
        "conditional": "Tryb warunkowy",
        "imperative": "Tryb rozkazujący",
        "infinitive": "Bezokolicznik",
        "subjunctive": "Tryb łączący",
        "past": "Czas przeszły",
        "present": "Czas teraźniejszy",
        "future": "Czas przyszły",
    },
    "de": {
        "conditional": "Konditional",
        "imperative": "Imperativ",
        "infinitive": "Infinitiv",
        "past": "Vergangenheit",
        "present": "Präsens",
        "future": "Futur",
    },
    "_default": {
        "conditional": "Conditional",
        "imperative": "Imperative",
        "infinitive": "Infinitive",
        "subjunctive": "Subjunctive",
        "past": "Past tense",
        "present": "Present tense",
        "future": "Future tense",
    },
}

# Degree of comparison per language
_DEGREE_BY_LANG: dict[str, dict[str, str]] = {
    "ru": {"comparative": "Сравнительная степень", "superlative": "Превосходная степень"},
    "pl": {"comparative": "Stopień wyższy", "superlative": "Stopień najwyższy"},
    "de": {"comparative": "Komparativ", "superlative": "Superlativ"},
    "cs": {"comparative": "Komparativ", "superlative": "Superlativ"},
    "_default": {"comparative": "Comparative", "superlative": "Superlative"},
}

# Person + number → subject pronoun prompt per language
_PERSON_BY_LANG: dict[str, dict[tuple[str, str], str]] = {
    "ru": {
        ("1", "singular"): "«я ...»",
        ("1", "plural"): "«мы ...»",
        ("2", "singular"): "«ты ...»",
        ("2", "plural"): "«вы ...»",
        ("3", "singular"): "«он / она ...»",
        ("3", "plural"): "«они ...»",
    },
    "pl": {
        ("1", "singular"): "«ja ...»",
        ("1", "plural"): "«my ...»",
        ("2", "singular"): "«ty ...»",
        ("2", "plural"): "«wy ...»",
        ("3", "singular"): "«on/ona/ono ...»",
        ("3", "plural"): "«oni/one ...»",
    },
    "de": {
        ("1", "singular"): "«ich ...»",
        ("1", "plural"): "«wir ...»",
        ("2", "singular"): "«du ...»",
        ("2", "plural"): "«ihr ...»",
        ("3", "singular"): "«er/sie/es ...»",
        ("3", "plural"): "«sie ...»",
    },
    "_default": {
        ("1", "singular"): "«I ...»",
        ("1", "plural"): "«We ...»",
        ("2", "singular"): "«You ...»",
        ("2", "plural"): "«You all ...»",
        ("3", "singular"): "«He / she / it ...»",
        ("3", "plural"): "«They ...»",
    },
}


def lang_lookup(table: dict[str, dict], lang_code: str) -> dict:
    return table.get(lang_code) or table.get("_default") or {}


_lang_lookup = lang_lookup  # keep private alias for internal callers


def _verb_specifics(tags: set[str], lang_code: str) -> str:
    person = next((p for p in ("1", "2", "3") if p in tags), None)
    number = "singular" if "singular" in tags else ("plural" if "plural" in tags else None)
    gender_map = _lang_lookup(_GENDER_BY_LANG, lang_code)
    gender = next((v for k, v in gender_map.items() if k in tags), "")

    person_map = _lang_lookup(_PERSON_BY_LANG, lang_code)
    pn_label = person_map.get((person, number), "") if person and number else ""  # type: ignore[arg-type]

    parts: list[str] = []
    if pn_label:
        parts.append(f"— {pn_label}")
    if gender:
        parts.append(f"({gender})")
    return " ".join(parts)


def make_drill_prompt(form_type: str, lang_code: str = "_default") -> str:
    """Return a native-language grammar prompt for the given form type."""
    # OpenRussian compact form types are always Russian
    if form_type in _RU_COMPACT_PROMPTS:
        return _RU_COMPACT_PROMPTS[form_type]

    tags = set(form_type.lower().split())
    case_map = _lang_lookup(_CASE_BY_LANG, lang_code)
    num_map = _lang_lookup(_NUM_BY_LANG, lang_code)
    gender_map = _lang_lookup(_GENDER_BY_LANG, lang_code)
    mood_map = _lang_lookup(_MOOD_BY_LANG, lang_code)

    num_str = num_map.get("singular", "") if "singular" in tags else (num_map.get("plural", "") if "plural" in tags else "")
    gender = next((v for k, v in gender_map.items() if k in tags), "")

    # Case
    for case_tag, case_name in case_map.items():
        if case_tag in tags:
            suffix = f" — {num_str}" if num_str else ""
            if gender:
                suffix += f" ({gender})"
            return f"{case_name}{suffix}"

    # Degree of comparison
    degree_map = _lang_lookup(_DEGREE_BY_LANG, lang_code)
    for deg_tag, deg_name in degree_map.items():
        if deg_tag in tags:
            return deg_name

    # Verb mood / tense
    all_moods = {**mood_map}
    for mood_tag, mood_name in all_moods.items():
        if mood_tag in tags:
            specifics = _verb_specifics(tags, lang_code)
            return f"{mood_name} {specifics}".strip()

    # Fallback
    result = form_type.replace("_", " ").strip()
    return result[0].upper() + result[1:] if result else "Correct form"


def normalize_answer(text: str) -> str:
    """Lowercase and strip combining diacritics (stress marks) for comparison."""
    nfd = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def reconstruct_sentence_plain(tokens: list[dict], sentence_index: int) -> str:
    """Return full sentence text with no word replaced."""
    sent_tokens = [t for t in tokens if t.get("si") == sentence_index]
    if not sent_tokens:
        return ""
    parts: list[str] = []
    for tok in sent_tokens:
        w: str = tok.get("w", "")
        pos: str = tok.get("pos", "")
        if not parts:
            parts.append(w)
        elif pos == "PUNCT" and w in (".", ",", "!", "?", ":", ";", ")", "»", "…"):
            parts[-1] = parts[-1] + w
        elif w in ("(", "«"):
            parts.append(w)
        else:
            parts.append(" " + w)
    return "".join(parts)


def _reconstruct_sentence(
    tokens: list[dict], sentence_index: int, blank_lemma: str
) -> tuple[str, bool]:
    """Return (sentence_with_blank, did_blank_a_token)."""
    sent_tokens = [t for t in tokens if t.get("si") == sentence_index]
    if not sent_tokens:
        return "", False

    parts: list[str] = []
    blanked = False
    for tok in sent_tokens:
        w: str = tok.get("w", "")
        lemma_key: str = tok.get("l", "")
        pos: str = tok.get("pos", "")

        if lemma_key == blank_lemma and not blanked:
            w = "___"
            blanked = True

        if not parts:
            parts.append(w)
        elif pos == "PUNCT" and w in (".", ",", "!", "?", ":", ";", ")", "»", "…"):
            parts[-1] = parts[-1] + w
        elif w in ("(", "«"):
            parts.append(w)
        else:
            parts.append(" " + w)

    return "".join(parts), blanked


class DrillSessionService:
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
            return DrillSessionResponse(
                session_id="", available=False, reason="no_active_language"
            )

        lang_code = language.code

        has_forms = await self._forms_repo.has_forms_for_language(db, lang_code)
        if not has_forms:
            return DrillSessionResponse(
                session_id="", available=False, reason="no_form_data"
            )

        rows_result = await db.execute(
            sa.select(Word.word, Word.lemma)
            .where(
                Word.user_id == user_id,
                Word.language_id == active_language_id,
                Word.status == "learning",
                Word.skip_in_vocabulary == False,  # noqa: E712
            )
        )
        learning_words = rows_result.all()

        if not learning_words:
            return DrillSessionResponse(
                session_id="", available=False, reason="no_learning_words"
            )

        drillable: list[tuple[str, list[WordForm]]] = []
        for row in learning_words:
            lemma = row.lemma or row.word
            forms = await self._forms_repo.get_forms(db, lemma, lang_code)
            if forms:
                drillable.append((lemma, forms))

        if not drillable:
            return DrillSessionResponse(
                session_id="", available=False, reason="no_drillable_words"
            )

        pool = random.sample(drillable, min(session_size, len(drillable)))
        questions: list[DrillQuestion] = []

        for lemma, forms in pool:
            q = await self._build_question(user_id, lemma, forms, lang_code, db)
            if q:
                questions.append(q)

        if not questions:
            return DrillSessionResponse(
                session_id="", available=False, reason="no_drillable_words"
            )

        return DrillSessionResponse(
            session_id=str(uuid.uuid4()),
            available=True,
            questions=questions,
        )

    async def _build_question(
        self,
        user_id: uuid.UUID,
        lemma: str,
        forms: list[WordForm],
        lang_code: str,
        db: AsyncSession,
    ) -> DrillQuestion | None:
        target = random.choice(forms)
        correct_form = target.forms[0]
        prompt = make_drill_prompt(target.form_type, lang_code)

        sentence: str | None = None
        if random.random() < _FILL_BLANK_RATIO:
            sentence = await self._find_sentence(user_id, lemma, db)

        if sentence:
            return DrillQuestion(
                id=str(uuid.uuid4()),
                type="fill_blank",
                lemma=lemma,
                display_lemma=lemma,
                prompt=prompt,
                form_type=target.form_type,
                sentence=sentence,
                correct_form=correct_form,
                accepted_forms=target.forms,
            )

        seen: set[str] = {correct_form}
        other_vals: list[str] = []
        for f in forms:
            v = f.forms[0]
            if f.form_type != target.form_type and v not in seen:
                seen.add(v)
                other_vals.append(v)
        random.shuffle(other_vals)
        distractors = other_vals[:3]

        if not distractors:
            return None

        options = [correct_form] + distractors
        random.shuffle(options)

        return DrillQuestion(
            id=str(uuid.uuid4()),
            type="multiple_choice",
            lemma=lemma,
            display_lemma=lemma,
            prompt=prompt,
            form_type=target.form_type,
            options=options,
            correct_form=correct_form,
            accepted_forms=target.forms,
        )

    async def _find_sentence(
        self, user_id: uuid.UUID, lemma: str, db: AsyncSession
    ) -> str | None:
        result = await db.execute(
            sa.select(ContentPage.tokens)
            .join(ContentItem, ContentPage.content_item_id == ContentItem.id)
            .where(
                ContentItem.user_id == user_id,
                ContentPage.tokens.op("@>")(
                    sa.cast(json.dumps([{"l": lemma}]), PgJSONB)
                ),
                ContentPage.tokens.is_not(None),
            )
            .limit(1)
        )
        tokens = result.scalar_one_or_none()
        if not tokens:
            return None

        target = next((t for t in tokens if t.get("l") == lemma), None)
        if not target:
            return None

        sentence, blanked = _reconstruct_sentence(tokens, target.get("si"), lemma)
        return sentence if blanked else None
