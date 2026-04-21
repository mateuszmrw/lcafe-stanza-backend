"""Exercise service for reading exercises."""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

import sqlalchemy as sa
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.content_page_repo import ContentPageRepository
from src.infrastructure.db.repositories.exercise_attempts_repo import ExerciseAttemptsRepository
from src.infrastructure.db.repositories.exercise_progress_repo import ExerciseProgressRepository
from src.infrastructure.db.repositories.word_repo import WordRepository

log = logging.getLogger(__name__)

_REDIS_SESSION_TTL = 30 * 60  # 30 minutes


def normalize_answer(answer: str) -> str:
    """Normalize answer for comparison: strip whitespace and lowercase."""
    return (answer or "").strip().lower()


# Case options for different languages (hardcoded for v1)
_CASE_OPTIONS: dict[str, list[str]] = {
    "ru": ["Nominative", "Genitive", "Dative", "Accusative", "Instrumental", "Prepositional"],
    "pl": ["Nominative", "Genitive", "Dative", "Accusative", "Locative", "Instrumental"],
    "de": ["Nominative", "Accusative", "Dative", "Genitive"],
}


class ExerciseService:
    """Core service for exercise generation, completion, and progress tracking."""

    def __init__(self) -> None:
        self._progress_repo = ExerciseProgressRepository()
        self._word_repo = WordRepository()
        self._page_repo = ContentPageRepository()
        self._attempts_repo = ExerciseAttemptsRepository()

    async def should_show(
        self,
        session: AsyncSession,
        redis: Redis | None,
        user_id: uuid.UUID,
        content_item_id: uuid.UUID,
        current_page: int,
        is_end_of_content: bool = False,
    ) -> tuple[bool, int]:
        """Determine if exercise prompt should be shown.

        Returns (should_show, candidate_count).

        Logic:
        - Load or create exercise_progress row with defaults
        - If not is_end_of_content:
            - If current_page < snooze_until_page: return (False, 0)
            - If current_page - last_exercise_page < user.exercise_interval_pages: return (False, 0)
        - Count eligible candidate words
        - If count == 0: update last_exercise_page, return (False, 0)
        - Return (True, count)
        """
        # Load progress or create with defaults
        progress = await self._progress_repo.get_or_create(session, user_id, content_item_id)

        # Check snooze (unless at end of content)
        if not is_end_of_content:
            if progress.snooze_until_page is not None and current_page < progress.snooze_until_page:
                return False, 0

        # Get user settings
        user_result = await session.execute(
            sa.text("SELECT exercise_interval_pages, exercises_enabled, active_language_id FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        user_row = user_result.first()
        if not user_row:
            return False, 0

        if not user_row.exercises_enabled:
            return False, 0

        interval_pages = user_row.exercise_interval_pages
        language_id = user_row.active_language_id

        if language_id is None:
            return False, 0

        # Check interval (unless at end of content)
        if not is_end_of_content:
            if current_page - progress.last_exercise_page < interval_pages:
                return False, 0

        # Count eligible candidates
        candidate_count = await self._count_candidates(
            session, user_id, language_id, content_item_id, progress.last_exercise_page
        )

        if candidate_count == 0:
            # Update last_exercise_page even if no candidates
            await self._progress_repo.update_last_exercise_page(
                session, user_id, content_item_id, current_page
            )
            return False, 0

        return True, candidate_count

    async def generate_session(
        self,
        session: AsyncSession,
        redis: Redis | None,
        user_id: uuid.UUID,
        content_item_id: uuid.UUID,
        current_page: int,
        mode: str = "inline",
    ) -> dict[str, Any]:
        """Generate exercise session.

        Args:
            session: DB session
            redis: Redis connection (required for storing session)
            user_id: User ID
            content_item_id: Content item ID
            current_page: Current page number
            mode: "inline" (since last exercise) or "practice" (all new/learning)

        Returns:
            {"session_id": str, "exercises": list[dict]}
        """
        progress = await self._progress_repo.get_or_create(session, user_id, content_item_id)

        # Get user data
        user_result = await session.execute(
            sa.text("SELECT active_language_id FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        user_row = user_result.first()
        if not user_row or user_row.active_language_id is None:
            return {"session_id": "", "exercises": []}

        language_id = user_row.active_language_id

        # Determine since_page based on mode
        since_page = 0 if mode == "practice" else progress.last_exercise_page

        # Fetch candidate words (up to 8)
        candidates = await self._get_candidate_words(
            session, user_id, language_id, content_item_id, since_page, limit=8
        )

        if not candidates:
            return {"session_id": "", "exercises": []}

        # Build exercises
        exercises: list[dict] = []
        for candidate in candidates:
            exercise = await self._build_exercise(session, candidate, content_item_id, language_id)
            if exercise is not None:
                exercises.append(exercise)
                if len(exercises) >= 8:
                    break

        # Store session in Redis
        session_id = str(uuid.uuid4())
        if redis and exercises:
            session_data = {
                "user_id": str(user_id),
                "content_item_id": str(content_item_id),
                "exercises": [
                    {
                        "id": ex["id"],
                        "word_id": ex["word_id"],
                        "type": ex["type"],
                        "correct_form": ex.get("correct_form", ""),
                        "correct_index": ex.get("correct_index", -1),
                        "exercise_type": ex["type"],
                    }
                    for ex in exercises
                ],
            }
            await redis.setex(
                f"exercises:{session_id}",
                _REDIS_SESSION_TTL,
                json.dumps(session_data),
            )

        return {"session_id": session_id, "exercises": exercises}

    async def complete_session(
        self,
        session: AsyncSession,
        redis: Redis | None,
        user_id: uuid.UUID,
        content_item_id: uuid.UUID,
        session_id: str,
        answers: list[dict],
        page: int,
    ) -> dict[str, Any]:
        """Complete exercise session and persist results.

        Args:
            session: DB session
            redis: Redis connection
            user_id: User ID
            content_item_id: Content item ID
            session_id: Session ID
            answers: List of {"exercise_id": str, "word_id": str, "answer": str, "exercise_type": str}
            page: Current page number

        Returns:
            {"results": list[dict], "upgrades": list[dict]}
        """
        # Get session from Redis
        if not redis:
            return {"results": [], "upgrades": []}

        session_data_json = await redis.get(f"exercises:{session_id}")
        if not session_data_json:
            return {"results": [], "upgrades": []}

        try:
            session_data = json.loads(session_data_json)
        except (json.JSONDecodeError, TypeError):
            return {"results": [], "upgrades": []}

        exercises_map = {ex["id"]: ex for ex in session_data.get("exercises", [])}

        # Score answers and collect results
        results: list[dict] = []
        correct_word_ids: list[uuid.UUID] = []
        attempts: list[dict] = []

        user_result = await session.execute(
            sa.text("SELECT active_language_id FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        user_row = user_result.first()
        language_id = user_row.active_language_id if user_row else None

        for answer in answers:
            exercise_id = answer["exercise_id"]
            word_id_str = answer["word_id"]
            exercise_type = answer["exercise_type"]

            try:
                word_id = uuid.UUID(word_id_str)
            except (ValueError, TypeError):
                continue

            ex_data = exercises_map.get(exercise_id)
            if not ex_data:
                continue

            # Score the answer
            is_correct = self._score_answer(answer["answer"], ex_data, exercise_type)

            results.append(
                {
                    "exercise_id": exercise_id,
                    "correct": is_correct,
                    "correct_form": ex_data.get("correct_form", ""),
                }
            )

            if is_correct:
                correct_word_ids.append(word_id)

            # Record attempt
            attempts.append(
                {
                    "user_id": user_id,
                    "word_id": word_id,
                    "content_item_id": content_item_id,
                    "exercise_type": exercise_type,
                    "correct": is_correct,
                }
            )

        # Persist attempts
        await self._attempts_repo.batch_insert(session, attempts)

        # Increment exercise_correct_rounds for correct answers
        if correct_word_ids:
            await self._word_repo.increment_exercise_rounds(session, correct_word_ids)

        # Apply status upgrades
        upgrades: list[dict] = []
        if language_id:
            ready_for_upgrade = await self._word_repo.get_words_ready_for_upgrade(
                session, user_id, language_id, threshold=2
            )

            for word in ready_for_upgrade:
                old_status = word.status
                new_status = self._compute_new_status(old_status)

                if new_status != old_status:
                    # Update status via upsert_with_status which resets exercise_correct_rounds
                    updated_word = await self._word_repo.upsert_with_status(
                        session,
                        user_id,
                        language_id,
                        word.word,
                        new_status,
                        lemma=word.lemma,
                        pos=word.pos,
                        reading=word.reading,
                        gender=word.gender,
                    )

                    upgrades.append(
                        {
                            "word_id": str(word.id),
                            "lemma": word.word,
                            "old_status": old_status,
                            "new_status": new_status,
                        }
                    )

        # Update progress
        await self._progress_repo.update_last_exercise_page(session, user_id, content_item_id, page)
        await self._progress_repo.clear_snooze(session, user_id, content_item_id)

        # Delete session from Redis
        if redis:
            await redis.delete(f"exercises:{session_id}")

        return {"results": results, "upgrades": upgrades}

    async def snooze(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        content_item_id: uuid.UUID,
        current_page: int,
    ) -> int:
        """Set snooze for the user.

        Args:
            session: DB session
            user_id: User ID
            content_item_id: Content item ID
            current_page: Current page number

        Returns:
            snooze_until_page
        """
        # Get user's interval setting
        user_result = await session.execute(
            sa.text("SELECT exercise_interval_pages FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        user_row = user_result.first()
        interval_pages = user_row.exercise_interval_pages if user_row else 5

        snooze_until_page = current_page + interval_pages

        # Ensure progress row exists
        await self._progress_repo.get_or_create(session, user_id, content_item_id)

        # Set snooze
        await self._progress_repo.set_snooze(session, user_id, content_item_id, snooze_until_page)

        return snooze_until_page

    # Private helper methods

    async def _count_candidates(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        content_item_id: uuid.UUID,
        since_page: int,
    ) -> int:
        """Count words eligible for exercises."""
        result = await session.execute(
            sa.text(
                """
                SELECT COUNT(DISTINCT w.id) as cnt
                FROM words w
                JOIN content_pages cp ON cp.content_item_id = :content_item_id
                CROSS JOIN LATERAL jsonb_array_elements(cp.tokens) AS elem(value)
                WHERE w.user_id = :user_id
                  AND w.language_id = :language_id
                  AND w.status = 'learning'
                  AND w.source_page_id IN (
                      SELECT id FROM content_pages WHERE content_item_id = :content_item_id
                  )
                  AND cp.page_number > :since_page
                  AND LOWER(elem.value->>'l') = w.word
                GROUP BY w.id, w.word, w.status
                HAVING COUNT(*) >= 2
                """
            ),
            {
                "user_id": user_id,
                "language_id": language_id,
                "content_item_id": content_item_id,
                "since_page": since_page,
            },
        )
        rows = result.fetchall()
        return len(rows)

    async def _get_candidate_words(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        language_id: int,
        content_item_id: uuid.UUID,
        since_page: int,
        limit: int = 8,
    ) -> list[dict]:
        """Fetch candidate words sorted by appearance count."""
        result = await session.execute(
            sa.text(
                """
                SELECT w.id, w.word as lemma, w.status, COUNT(*) as appearances
                FROM words w
                JOIN content_pages cp ON cp.content_item_id = :content_item_id
                CROSS JOIN LATERAL jsonb_array_elements(cp.tokens) AS elem(value)
                WHERE w.user_id = :user_id
                  AND w.language_id = :language_id
                  AND w.status = 'learning'
                  AND w.source_page_id IN (
                      SELECT id FROM content_pages WHERE content_item_id = :content_item_id
                  )
                  AND cp.page_number > :since_page
                  AND LOWER(elem.value->>'l') = w.word
                GROUP BY w.id, w.word, w.status
                HAVING COUNT(*) >= 2
                ORDER BY COUNT(*) DESC, w.created_at DESC
                LIMIT :limit
                """
            ),
            {
                "user_id": user_id,
                "language_id": language_id,
                "content_item_id": content_item_id,
                "since_page": since_page,
                "limit": limit,
            },
        )
        return [
            {
                "word_id": str(row.id),
                "lemma": row.lemma,
                "status": row.status,
                "appearances": row.appearances,
            }
            for row in result
        ]

    async def _build_exercise(
        self,
        session: AsyncSession,
        candidate: dict,
        content_item_id: uuid.UUID,
        language_id: int,
    ) -> dict | None:
        """Build a single exercise for a candidate word.

        Tries Cloze → Grammar → Meaning Recall.
        Returns exercise dict or None if no type available.
        """
        lemma = candidate["lemma"]
        word_id = candidate["word_id"]

        # Try Cloze
        cloze_ex = await self._build_cloze(session, lemma, word_id, content_item_id)
        if cloze_ex:
            return cloze_ex

        # Try Grammar Micro-Drill
        grammar_ex = await self._build_grammar_micro_drill(session, lemma, word_id, content_item_id, language_id)
        if grammar_ex:
            return grammar_ex

        # Try Meaning Recall
        meaning_ex = await self._build_meaning_recall(session, lemma, word_id, language_id)
        if meaning_ex:
            return meaning_ex

        return None

    async def _build_cloze(
        self,
        session: AsyncSession,
        lemma: str,
        word_id: str,
        content_item_id: uuid.UUID,
    ) -> dict | None:
        """Build a Cloze exercise."""
        sentence_data = await self._page_repo.find_sentence_for_lemma(session, lemma, content_item_id)
        if not sentence_data:
            return None

        tokens = sentence_data["tokens"]
        target_index = sentence_data["target_index"]
        target_token = tokens[target_index]

        # Build sentence with blank
        sentence_tokens = [t["w"] for t in tokens]
        sentence_tokens[target_index] = "___"

        return {
            "id": str(uuid.uuid4()),
            "type": "cloze",
            "word_id": word_id,
            "lemma": lemma,
            "sentence_tokens": sentence_tokens,
            "blank_index": target_index,
            "correct_form": target_token["w"],
        }

    async def _build_grammar_micro_drill(
        self,
        session: AsyncSession,
        lemma: str,
        word_id: str,
        content_item_id: uuid.UUID,
        language_id: int,
    ) -> dict | None:
        """Build a Grammar Micro-Drill exercise."""
        sentence_data = await self._page_repo.find_sentence_for_lemma(session, lemma, content_item_id)
        if not sentence_data:
            return None

        tokens = sentence_data["tokens"]
        target_index = sentence_data["target_index"]
        target_token = tokens[target_index]

        # Check if target token has the right dep_rel and feats
        if target_token.get("dep_rel") not in ("obl", "nmod"):
            return None

        feats_str = target_token.get("feats", "")
        feats = self._parse_feats(feats_str)
        if "Case" not in feats:
            return None

        correct_case = feats["Case"]

        # Find governing preposition
        dep_head = target_token.get("dep_head", 0)
        if dep_head <= 0 or dep_head > len(tokens):
            return None

        gov_token = tokens[dep_head - 1]
        if gov_token.get("pos") != "ADP":
            return None

        # Build prompt
        preposition = gov_token["w"]
        word_surface = target_token["w"]
        prompt = f'You saw «{preposition} {word_surface}» — what case is «{word_surface}»?'

        # Get case options for this language
        lang_result = await session.execute(
            sa.text("SELECT code FROM languages WHERE id = :lang_id"),
            {"lang_id": language_id},
        )
        lang_row = lang_result.first()
        lang_code = lang_row.code if lang_row else "ru"

        all_cases = _CASE_OPTIONS.get(lang_code, _CASE_OPTIONS["ru"])

        # Ensure correct case is in options and build final options list
        if correct_case not in all_cases:
            return None

        # Pick 4 cases including the correct one
        options = [correct_case]
        for case in all_cases:
            if case != correct_case and len(options) < 4:
                options.append(case)

        correct_index = options.index(correct_case)

        return {
            "id": str(uuid.uuid4()),
            "type": "grammar_micro_drill",
            "word_id": word_id,
            "lemma": lemma,
            "prompt": prompt,
            "options": options,
            "correct_index": correct_index,
        }

    async def _build_meaning_recall(
        self,
        session: AsyncSession,
        lemma: str,
        word_id: str,
        language_id: int,
    ) -> dict | None:
        """Build a Meaning Recall exercise."""
        # Get language code and user's native language
        lang_result = await session.execute(
            sa.text(
                """
                SELECT l.code, u.native_language_code
                FROM languages l
                JOIN users u ON TRUE
                WHERE l.id = :lang_id
                LIMIT 1
                """
            ),
            {"lang_id": language_id},
        )
        lang_row = lang_result.first()
        if not lang_row:
            return None

        lang_code = lang_row.code
        native_lang = lang_row.native_language_code or "en"

        # Get translation from dictionary entries
        translation_result = await session.execute(
            sa.text(
                """
                SELECT glosses FROM dictionary_entries
                WHERE source_lang = :lang_code AND word = :lemma
                LIMIT 1
                """
            ),
            {"lang_code": lang_code, "lemma": lemma},
        )
        trans_row = translation_result.first()
        if not trans_row or not trans_row.glosses:
            return None

        # Extract first gloss as correct answer
        glosses = trans_row.glosses
        correct_translation = glosses[0] if isinstance(glosses, list) and glosses else None

        if not correct_translation:
            return None

        # Get distractors
        distractors = await self._get_distractors(session, correct_translation, language_id, count=3)

        # Build options
        options = [correct_translation] + distractors
        import random

        random.shuffle(options)
        correct_index = options.index(correct_translation)

        return {
            "id": str(uuid.uuid4()),
            "type": "meaning_recall",
            "word_id": word_id,
            "lemma": lemma,
            "sentence": f"I found {lemma}",  # Placeholder
            "highlighted_word": lemma,
            "options": options,
            "correct_index": correct_index,
        }

    async def _get_distractors(
        self,
        session: AsyncSession,
        correct: str,
        language_id: int,
        count: int = 3,
    ) -> list[str]:
        """Get distractor translations from dictionary."""
        # Get language code
        lang_result = await session.execute(
            sa.text("SELECT code FROM languages WHERE id = :lang_id"),
            {"lang_id": language_id},
        )
        lang_row = lang_result.first()
        lang_code = lang_row.code if lang_row else "ru"

        # Get random glosses from other words
        result = await session.execute(
            sa.text(
                """
                SELECT DISTINCT glosses FROM dictionary_entries
                WHERE source_lang = :lang_code
                ORDER BY RANDOM()
                LIMIT :count
                """
            ),
            {"lang_code": lang_code, "count": count * 2},  # Get more to filter
        )
        rows = result.fetchall()

        # Extract unique distractors from glosses
        distractors: list[str] = []
        for row in rows:
            if row.glosses and isinstance(row.glosses, list):
                for gloss in row.glosses:
                    if gloss != correct and gloss not in distractors:
                        distractors.append(gloss)
                        if len(distractors) >= count:
                            break
            if len(distractors) >= count:
                break

        # Pad with generic words if needed
        if len(distractors) < count:
            generic_words = ["word", "thing", "place", "person", "action", "quality"]
            for generic in generic_words:
                if len(distractors) >= count:
                    break
                if generic != correct and generic not in distractors:
                    distractors.append(generic)

        return distractors[:count]

    def _score_answer(self, answer: str, exercise_data: dict, exercise_type: str) -> bool:
        """Score an answer against the correct response."""
        if exercise_type == "cloze":
            correct_form = exercise_data.get("correct_form", "")
            return normalize_answer(answer) == normalize_answer(correct_form)
        elif exercise_type == "meaning_recall":
            correct_index = exercise_data.get("correct_index", -1)
            try:
                user_index = int(answer)
                return user_index == correct_index
            except (ValueError, TypeError):
                return False
        elif exercise_type == "grammar_micro_drill":
            correct_index = exercise_data.get("correct_index", -1)
            try:
                user_index = int(answer)
                return user_index == correct_index
            except (ValueError, TypeError):
                return False

        return False

    def _compute_new_status(self, old_status: str) -> str:
        """Compute new status based on upgrade logic."""
        if old_status == "new":
            return "learning"
        elif old_status == "learning":
            return "known"
        return old_status

    def _parse_feats(self, feats_str: str) -> dict[str, str]:
        """Parse morphological features string into dict."""
        result = {}
        if not feats_str:
            return result
        for kv in feats_str.split("|"):
            if "=" in kv:
                k, _, v = kv.partition("=")
                result[k] = v
        return result
