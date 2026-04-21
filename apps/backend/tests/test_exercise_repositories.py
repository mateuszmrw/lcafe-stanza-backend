"""Tests for exercise repositories."""
import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.users.models import UserCreate
from src.infrastructure.db.models.content import ContentItem
from src.infrastructure.db.models.exercises import ExerciseAttempt, ExerciseProgress
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.providers import Provider
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.exercise_attempts_repo import (
    ExerciseAttemptsRepository,
)
from src.infrastructure.db.repositories.exercise_progress_repo import (
    ExerciseProgressRepository,
)
from src.infrastructure.db.repositories.user_repo import UserRepository
from src.infrastructure.db.repositories.word_repo import WordRepository


@pytest.fixture
async def setup_user_language_content(test_session: AsyncSession):
    """Set up user, language, and content for tests."""
    # Create user
    user_repo = UserRepository()
    user = await user_repo.create(
        test_session,
        UserCreate(email="test@example.com", username="testuser", password="pass123"),
    )
    await test_session.flush()

    # Create language
    provider = Provider(slug="stanza", name="Stanza NLP", type="nlp")
    test_session.add(provider)
    await test_session.flush()

    language = Language(code="ru", name="Russian")
    test_session.add(language)
    await test_session.flush()

    # Create content item
    content_item = ContentItem(
        user_id=user.id,
        language_id=language.id,
        type="book",
        title="Test Book",
        status="completed",
    )
    test_session.add(content_item)
    await test_session.flush()

    # Create words for the user
    word1 = Word(
        id=uuid.uuid4(),
        user_id=user.id,
        language_id=language.id,
        word="сон",
        lemma="сон",
        pos="NOUN",
        status="new",
        exercise_correct_rounds=0,
    )
    word2 = Word(
        id=uuid.uuid4(),
        user_id=user.id,
        language_id=language.id,
        word="книга",
        lemma="книга",
        pos="NOUN",
        status="learning",
        exercise_correct_rounds=0,
    )
    test_session.add(word1)
    test_session.add(word2)
    await test_session.flush()
    await test_session.commit()

    return user, language, content_item, word1, word2


class TestExerciseProgressRepository:
    """Test ExerciseProgressRepository."""

    @pytest.mark.asyncio
    async def test_get_or_create_inserts_new_progress(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """get_or_create should insert a new row with defaults if missing."""
        user, _, content_item, _, _ = setup_user_language_content
        repo = ExerciseProgressRepository()

        progress = await repo.get_or_create(
            test_session, user.id, content_item.id
        )

        assert progress is not None
        assert progress.user_id == user.id
        assert progress.content_item_id == content_item.id
        assert progress.last_exercise_page == 0
        assert progress.snooze_until_page is None

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """get_or_create should return existing row if it exists."""
        user, _, content_item, _, _ = setup_user_language_content
        repo = ExerciseProgressRepository()

        # Insert initial
        progress1 = await repo.get_or_create(
            test_session, user.id, content_item.id
        )
        await test_session.flush()

        # Get again
        progress2 = await repo.get_or_create(
            test_session, user.id, content_item.id
        )

        assert progress1.user_id == progress2.user_id
        assert progress1.content_item_id == progress2.content_item_id

    @pytest.mark.asyncio
    async def test_update_last_exercise_page(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """update_last_exercise_page should update the page number."""
        user, _, content_item, _, _ = setup_user_language_content
        repo = ExerciseProgressRepository()

        progress = await repo.get_or_create(
            test_session, user.id, content_item.id
        )
        await test_session.flush()

        await repo.update_last_exercise_page(
            test_session, user.id, content_item.id, 42
        )
        await test_session.flush()

        # Refresh from DB
        result = await repo.get_or_create(
            test_session, user.id, content_item.id
        )
        assert result.last_exercise_page == 42

    @pytest.mark.asyncio
    async def test_set_snooze(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """set_snooze should set snooze_until_page."""
        user, _, content_item, _, _ = setup_user_language_content
        repo = ExerciseProgressRepository()

        progress = await repo.get_or_create(
            test_session, user.id, content_item.id
        )
        await test_session.flush()

        await repo.set_snooze(
            test_session, user.id, content_item.id, snooze_until_page=10
        )
        await test_session.flush()

        result = await repo.get_or_create(
            test_session, user.id, content_item.id
        )
        assert result.snooze_until_page == 10

    @pytest.mark.asyncio
    async def test_clear_snooze(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """clear_snooze should set snooze_until_page to None."""
        user, _, content_item, _, _ = setup_user_language_content
        repo = ExerciseProgressRepository()

        progress = await repo.get_or_create(
            test_session, user.id, content_item.id
        )
        await repo.set_snooze(
            test_session, user.id, content_item.id, snooze_until_page=10
        )
        await test_session.flush()

        await repo.clear_snooze(test_session, user.id, content_item.id)
        await test_session.flush()

        result = await repo.get_or_create(
            test_session, user.id, content_item.id
        )
        assert result.snooze_until_page is None


class TestExerciseAttemptsRepository:
    """Test ExerciseAttemptsRepository."""

    @pytest.mark.asyncio
    async def test_batch_insert(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """batch_insert should insert multiple exercise attempts."""
        user, _, content_item, word1, word2 = setup_user_language_content
        repo = ExerciseAttemptsRepository()

        attempts = [
            {
                "user_id": user.id,
                "word_id": word1.id,
                "content_item_id": content_item.id,
                "exercise_type": "cloze",
                "correct": True,
            },
            {
                "user_id": user.id,
                "word_id": word2.id,
                "content_item_id": content_item.id,
                "exercise_type": "meaning_recall",
                "correct": False,
            },
        ]

        await repo.batch_insert(test_session, attempts)
        await test_session.flush()

        # Verify rows were inserted
        from sqlalchemy import select
        result = await test_session.execute(
            select(ExerciseAttempt).where(ExerciseAttempt.user_id == user.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 2
        assert rows[0].exercise_type == "cloze"
        assert rows[0].correct is True
        assert rows[1].exercise_type == "meaning_recall"
        assert rows[1].correct is False

    @pytest.mark.asyncio
    async def test_batch_insert_empty_list(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """batch_insert with empty list should not raise an error."""
        repo = ExerciseAttemptsRepository()
        await repo.batch_insert(test_session, [])
        await test_session.flush()
        # Should complete without error

    @pytest.mark.asyncio
    async def test_count_correct_rounds_since(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """count_correct_rounds_since should count correct attempts since a timestamp."""
        user, _, content_item, word1, _ = setup_user_language_content
        repo = ExerciseAttemptsRepository()

        # Insert attempts
        now = datetime.now()
        attempts = [
            {
                "user_id": user.id,
                "word_id": word1.id,
                "content_item_id": content_item.id,
                "exercise_type": "cloze",
                "correct": True,
            },
            {
                "user_id": user.id,
                "word_id": word1.id,
                "content_item_id": content_item.id,
                "exercise_type": "cloze",
                "correct": True,
            },
            {
                "user_id": user.id,
                "word_id": word1.id,
                "content_item_id": content_item.id,
                "exercise_type": "cloze",
                "correct": False,
            },
        ]
        await repo.batch_insert(test_session, attempts)
        await test_session.flush()

        count = await repo.count_correct_rounds_since(
            test_session, word1.id, user.id, since_round_start=now
        )
        assert count == 2


class TestWordRepositoryExtensions:
    """Test extensions to WordRepository for exercise scoring."""

    @pytest.mark.asyncio
    async def test_increment_exercise_rounds(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """increment_exercise_rounds should increment the counter for given words."""
        _, _, _, word1, word2 = setup_user_language_content
        repo = WordRepository()

        await repo.increment_exercise_rounds(
            test_session, [word1.id, word2.id]
        )
        await test_session.flush()

        # Refresh from DB
        await test_session.refresh(word1)
        await test_session.refresh(word2)

        assert word1.exercise_correct_rounds == 1
        assert word2.exercise_correct_rounds == 1

    @pytest.mark.asyncio
    async def test_increment_exercise_rounds_multiple_times(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """increment_exercise_rounds should stack on multiple calls."""
        _, _, _, word1, _ = setup_user_language_content
        repo = WordRepository()

        await repo.increment_exercise_rounds(test_session, [word1.id])
        await test_session.flush()
        await repo.increment_exercise_rounds(test_session, [word1.id])
        await test_session.flush()

        await test_session.refresh(word1)
        assert word1.exercise_correct_rounds == 2

    @pytest.mark.asyncio
    async def test_reset_exercise_rounds(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """reset_exercise_rounds should reset counter to 0."""
        _, _, _, word1, word2 = setup_user_language_content
        repo = WordRepository()

        # Bump the counter first
        await repo.increment_exercise_rounds(test_session, [word1.id, word2.id])
        await repo.increment_exercise_rounds(test_session, [word1.id])
        await test_session.flush()

        await test_session.refresh(word1)
        assert word1.exercise_correct_rounds == 2

        # Reset
        await repo.reset_exercise_rounds(test_session, [word1.id])
        await test_session.flush()

        await test_session.refresh(word1)
        assert word1.exercise_correct_rounds == 0

    @pytest.mark.asyncio
    async def test_get_words_ready_for_upgrade(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """get_words_ready_for_upgrade should return words with >= threshold rounds."""
        user, language, _, word1, word2 = setup_user_language_content
        repo = WordRepository()

        # Increment word1 to 2, word2 to 1
        await repo.increment_exercise_rounds(test_session, [word1.id, word2.id])
        await repo.increment_exercise_rounds(test_session, [word1.id])
        await test_session.flush()

        # word1 should be ready (2 >= 2), word2 should not be (1 < 2)
        ready = await repo.get_words_ready_for_upgrade(
            test_session, user.id, language.id, threshold=2
        )

        assert len(ready) == 1
        assert ready[0].id == word1.id

    @pytest.mark.asyncio
    async def test_get_words_ready_for_upgrade_filters_status(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """get_words_ready_for_upgrade should only return new/learning words."""
        user, language, _, word1, word2 = setup_user_language_content
        repo = WordRepository()

        # Set word2 to 'known' (should be filtered out)
        word2.status = "known"
        await test_session.flush()

        # Both have 2 rounds
        await repo.increment_exercise_rounds(test_session, [word1.id, word2.id])
        await repo.increment_exercise_rounds(test_session, [word1.id, word2.id])
        await test_session.flush()

        ready = await repo.get_words_ready_for_upgrade(
            test_session, user.id, language.id, threshold=2
        )

        # Only word1 (status='new') should be returned, not word2 (status='known')
        assert len(ready) == 1
        assert ready[0].id == word1.id
        assert ready[0].status == "new"


class TestUserRepositoryExtensions:
    """Test extensions to UserRepository for exercise interval."""

    @pytest.mark.asyncio
    async def test_update_exercise_interval(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """update_exercise_interval should update the interval setting."""
        user, _, _, _, _ = setup_user_language_content
        repo = UserRepository()

        await repo.update_exercise_interval(test_session, user.id, 10)
        await test_session.flush()

        # Refresh from DB
        updated_user = await repo.find_by_id(test_session, user.id)
        assert updated_user.exercise_interval_pages == 10

    @pytest.mark.asyncio
    async def test_update_exercise_interval_clamps_to_min_1(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """update_exercise_interval should clamp to minimum 1."""
        user, _, _, _, _ = setup_user_language_content
        repo = UserRepository()

        await repo.update_exercise_interval(test_session, user.id, 0)
        await test_session.flush()

        updated_user = await repo.find_by_id(test_session, user.id)
        assert updated_user.exercise_interval_pages == 1

    @pytest.mark.asyncio
    async def test_update_exercise_interval_negative_clamps_to_1(
        self, test_session: AsyncSession, setup_user_language_content
    ):
        """update_exercise_interval should clamp negative values to 1."""
        user, _, _, _, _ = setup_user_language_content
        repo = UserRepository()

        await repo.update_exercise_interval(test_session, user.id, -5)
        await test_session.flush()

        updated_user = await repo.find_by_id(test_session, user.id)
        assert updated_user.exercise_interval_pages == 1
