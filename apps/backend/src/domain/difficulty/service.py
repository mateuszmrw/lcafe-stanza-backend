"""Word difficulty scoring service."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.dictionary_entries import DictionaryEntry
from src.infrastructure.db.models.openrussian import OpenRussianWord
from src.infrastructure.db.models.word_frequencies import WordFrequency
from src.infrastructure.db.models.words import Word

_MIN_EXPOSURES = 3
_MAX_RANK = 50_000
_MAX_FORMS = 20


def compute_score(
    freq_rank: int | None,
    form_count: int,
    lookup_count: int,
    exposure_count: int,
) -> int | None:
    """Compute difficulty score 0-100. Returns None if below exposure threshold."""
    if exposure_count < _MIN_EXPOSURES:
        return None

    # Frequency: higher rank = rarer = harder
    if freq_rank is None:
        freq_score = 0.5  # neutral when no data
    else:
        freq_score = min(freq_rank / _MAX_RANK, 1.0)

    # Inflection complexity: more forms = harder
    inflection_score = min(form_count / _MAX_FORMS, 1.0) if form_count > 0 else 0.0

    # Personal: lookup ratio (capped at 1.0)
    lookup_ratio = min(lookup_count / max(exposure_count, 1), 1.0)

    return round((0.3 * freq_score + 0.3 * inflection_score + 0.4 * lookup_ratio) * 100)


class DifficultyService:
    async def batch_get_freq_ranks(
        self, session: AsyncSession, language_code: str, lemmas: list[str]
    ) -> dict[str, int]:
        """Return {lemma: rank} for matching words."""
        if not lemmas:
            return {}
        result = await session.execute(
            sa.select(WordFrequency.lemma, WordFrequency.rank).where(
                WordFrequency.language_code == language_code,
                WordFrequency.lemma.in_(lemmas),
            )
        )
        return {row.lemma: row.rank for row in result}

    async def batch_get_form_counts(
        self, session: AsyncSession, lemmas: list[str], language_code: str
    ) -> dict[str, int]:
        """Return {lemma: form_count} from dictionary tables."""
        if not lemmas:
            return {}

        counts: dict[str, int] = {}

        # OpenRussian (Russian-specific, has structured forms array)
        if language_code == "ru":
            result = await session.execute(
                sa.select(
                    OpenRussianWord.bare,
                    sa.func.jsonb_array_length(OpenRussianWord.forms).label("cnt"),
                ).where(OpenRussianWord.bare.in_(lemmas))
            )
            for row in result:
                if row.cnt and row.cnt > 0:
                    counts[row.bare] = row.cnt

        # Wiktionary (any language, forms is JSON — use json_array_length, not jsonb_array_length)
        result = await session.execute(
            sa.select(
                DictionaryEntry.word,
                sa.func.json_array_length(DictionaryEntry.forms).label("cnt"),
            ).where(
                DictionaryEntry.word.in_(lemmas),
                DictionaryEntry.forms.isnot(None),
            )
        )
        for row in result:
            if row.cnt and row.cnt > 0 and row.word not in counts:
                counts[row.word] = row.cnt

        return counts

    async def recompute_for_words(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        language_code: str,
        lemmas: list[str],
    ) -> int:
        """Recompute difficulty_score for specific words. Returns count updated."""
        if not lemmas:
            return 0

        # Batch fetch all signals
        freq_ranks = await self.batch_get_freq_ranks(session, language_code, lemmas)
        form_counts = await self.batch_get_form_counts(session, lemmas, language_code)

        # Fetch current word data
        result = await session.execute(
            sa.select(Word.id, Word.word, Word.lookup_count, Word.exposure_count).where(
                Word.user_id == user_id,
                Word.language_id == language_id,
                Word.word.in_(lemmas),
            )
        )

        updated = 0
        for row in result:
            score = compute_score(
                freq_rank=freq_ranks.get(row.word),
                form_count=form_counts.get(row.word, 0),
                lookup_count=row.lookup_count,
                exposure_count=row.exposure_count,
            )
            await session.execute(
                sa.update(Word).where(Word.id == row.id).values(difficulty_score=score)
            )
            updated += 1

        return updated

    async def recompute_all(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        language_code: str,
    ) -> int:
        """Recompute difficulty for ALL words in a language. Returns count updated."""
        result = await session.execute(
            sa.select(Word.word).where(
                Word.user_id == user_id,
                Word.language_id == language_id,
            )
        )
        all_lemmas = [row.word for row in result]
        return await self.recompute_for_words(
            session, user_id, language_id, language_code, all_lemmas
        )
