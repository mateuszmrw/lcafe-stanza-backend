from __future__ import annotations

from dataclasses import dataclass, field

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.dictionary_entries import DictionaryEntry
from src.infrastructure.db.models.openrussian import OpenRussianWord

# kaikki.org Wiktionary exports include internal template metadata as "forms".
# Tags that make a form entry useless for grammar drills:
_JUNK_FORM_TAGS = frozenset({
    "inflection-template",
    "table-tags",
    "no-table-tags",
    "error-unrecognized-form",
    "canonical",
    "romanization",
    # "alternative" alone gives no case/tense context — skip if it's the only tag.
    # handled separately below so we keep ["alternative", "genitive", ...] entries.
})

# Form values that are Wiktionary template names or metadata strings, never real words.
_JUNK_FORM_VALUES = frozenset({
    "no-table-tags",
    "table-tags",
    "inflection-template",
    "-",
    "—",
    "–",
})

# Whitelist of tags that carry actual grammatical information useful for drills.
# A form entry must have at least one of these to be included.
_GRAMMATICAL_TAGS = frozenset({
    # Cases
    "nominative", "genitive", "dative", "accusative",
    "instrumental", "locative", "prepositional", "vocative", "ablative",
    # Number
    "singular", "plural",
    # Gender / animacy
    "masculine", "feminine", "neuter", "virile", "non-virile", "non virile",
    "animate", "inanimate",
    # Tense / mood
    "past", "present", "future",
    "conditional", "imperative", "subjunctive", "infinitive",
    # Person
    "1", "2", "3",
    # Aspect
    "perfective", "imperfective",
    # Degree of comparison
    "comparative", "superlative",
    # Short-form adjectives (Russian)
    "short-form",
})


def _is_template_slug(form: str) -> bool:
    """Detect Wiktionary template slugs like 'pl-decl-noun-m-in'."""
    if form in _JUNK_FORM_VALUES:
        return True
    return (
        "-" in form
        and " " not in form
        and form.count("-") >= 2
        and form.replace("-", "").replace("_", "").isascii()
        and form.replace("-", "").replace("_", "").isalpha()
    )


def _has_grammatical_tags(tags: list[str]) -> bool:
    """Return True only when at least one tag carries grammatical info useful for a drill."""
    return bool(set(tags) & _GRAMMATICAL_TAGS)


@dataclass
class WordForm:
    form_type: str
    forms: list[str] = field(default_factory=list)  # primary + optional variant


class DictionaryFormsRepository:
    async def get_forms(
        self, session: AsyncSession, lemma: str, language_code: str
    ) -> list[WordForm]:
        if language_code == "ru":
            return await self._openrussian_forms(session, lemma)
        return await self._dict_entry_forms(session, lemma, language_code)

    async def _openrussian_forms(
        self, session: AsyncSession, lemma: str
    ) -> list[WordForm]:
        result = await session.execute(
            sa.select(OpenRussianWord.forms)
            .where(OpenRussianWord.bare == lemma.lower())
            .limit(1)
        )
        raw = result.scalar_one_or_none()
        if not raw:
            return []

        out: list[WordForm] = []
        for entry in raw:
            form_type = (entry.get("form_type") or "").strip()
            form1 = (entry.get("form1") or "").strip()
            form2 = (entry.get("form2") or "").strip()
            if not form1:
                continue
            accepted = [form1]
            if form2 and form2 != form1:
                accepted.append(form2)
            out.append(WordForm(form_type=form_type, forms=accepted))
        return out

    async def _dict_entry_forms(
        self, session: AsyncSession, lemma: str, language_code: str
    ) -> list[WordForm]:
        result = await session.execute(
            sa.select(DictionaryEntry.forms)
            .where(
                DictionaryEntry.word == lemma.lower(),
                DictionaryEntry.source_lang == language_code,
            )
            .limit(1)
        )
        raw = result.scalar_one_or_none()
        if not raw:
            return []

        out: list[WordForm] = []
        for entry in raw:
            form_value = (entry.get("form") or "").strip()
            tags: list[str] = entry.get("tags") or []
            tag_set = set(tags)

            if not form_value:
                continue
            if form_value in _JUNK_FORM_VALUES:
                continue
            if tag_set & _JUNK_FORM_TAGS:
                continue
            if _is_template_slug(form_value):
                continue
            if not _has_grammatical_tags(tags):
                continue

            form_type = " ".join(str(t) for t in tags) if tags else "form"
            out.append(WordForm(form_type=form_type, forms=[form_value]))
        return out

    async def has_forms_for_language(
        self, session: AsyncSession, language_code: str
    ) -> bool:
        if language_code == "ru":
            count = await session.scalar(
                sa.select(sa.func.count()).select_from(OpenRussianWord)
            )
            return (count or 0) > 0

        count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(DictionaryEntry)
            .where(DictionaryEntry.source_lang == language_code)
        )
        return (count or 0) > 0
