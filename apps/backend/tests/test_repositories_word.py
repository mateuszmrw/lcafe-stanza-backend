import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.users import User
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.word_repo import WordRepository


@pytest.fixture
def word_repo():
    """Provide a WordRepository instance."""
    return WordRepository()


@pytest.fixture
async def test_user_id(test_session: AsyncSession) -> uuid.UUID:
    """Create a real user in the DB and return its ID."""
    user = User(
        email=f"wordtest-{uuid.uuid4().hex[:8]}@example.com",
        username=f"worduser-{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
    )
    test_session.add(user)
    await test_session.flush()
    return user.id


@pytest.fixture
async def test_language_id(test_session: AsyncSession) -> int:
    """Create a real language in the DB and return its ID."""
    lang = Language(code=f"tl{uuid.uuid4().hex[:4]}", name="TestLang")
    test_session.add(lang)
    await test_session.flush()
    return lang.id


class TestWordRepositoryBulkUpsert:
    """Test WordRepository.bulk_upsert()."""

    @pytest.mark.asyncio
    async def test_bulk_upsert_empty_list(
        self,
        test_session: AsyncSession,
        word_repo: WordRepository,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test bulk upsert with empty list does nothing."""
        await word_repo.bulk_upsert(test_session, test_user_id, test_language_id, [])
        await test_session.flush()

        # Should not raise and should not create any words
        words = await test_session.execute(
            __import__("sqlalchemy").select(Word).where(
                Word.user_id == test_user_id
            )
        )
        assert len(list(words.scalars().all())) == 0

    @pytest.mark.asyncio
    async def test_bulk_upsert_new_words(
        self,
        test_session: AsyncSession,
        word_repo: WordRepository,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test bulk upsert inserts new words."""
        rows = [
            {
                "user_id": test_user_id,
                "language_id": test_language_id,
                "word": "hello",
                "lemma": "hello",
                "pos": "NOUN",
                "reading": "",
            },
            {
                "user_id": test_user_id,
                "language_id": test_language_id,
                "word": "world",
                "lemma": "world",
                "pos": "NOUN",
                "reading": "",
            },
        ]

        await word_repo.bulk_upsert(test_session, test_user_id, test_language_id, rows)
        await test_session.flush()

        # Verify both words were inserted
        import sqlalchemy as sa

        result = await test_session.execute(
            sa.select(Word)
            .where(
                Word.user_id == test_user_id,
                Word.language_id == test_language_id,
            )
            .order_by(Word.word)
        )
        words = list(result.scalars().all())
        assert len(words) == 2
        assert words[0].word == "hello"
        assert words[1].word == "world"

    @pytest.mark.asyncio
    async def test_bulk_upsert_preserves_status(
        self,
        test_session: AsyncSession,
        word_repo: WordRepository,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test that bulk upsert does NOT overwrite existing word status."""
        # First, create a word with 'learning' status
        word = Word(
            user_id=test_user_id,
            language_id=test_language_id,
            word="python",
            lemma="python",
            pos="NOUN",
            status="learning",
        )
        test_session.add(word)
        await test_session.flush()

        # Now bulk upsert the same word (should preserve status)
        rows = [
            {
                "user_id": test_user_id,
                "language_id": test_language_id,
                "word": "python",
                "lemma": "python",
                "pos": "NOUN",
                "reading": "",
            }
        ]

        await word_repo.bulk_upsert(test_session, test_user_id, test_language_id, rows)
        await test_session.flush()

        # Verify the word still has 'learning' status
        import sqlalchemy as sa

        result = await test_session.execute(
            sa.select(Word).where(
                Word.user_id == test_user_id,
                Word.word == "python",
            )
        )
        updated_word = result.scalar_one()
        assert updated_word.status == "learning"  # Should NOT change to 'new'

    @pytest.mark.asyncio
    async def test_bulk_upsert_mixed_new_and_existing(
        self,
        test_session: AsyncSession,
        word_repo: WordRepository,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test bulk upsert with mix of new and existing words."""
        # Create one word with 'known' status
        existing_word = Word(
            user_id=test_user_id,
            language_id=test_language_id,
            word="python",
            lemma="python",
            pos="NOUN",
            status="known",
        )
        test_session.add(existing_word)
        await test_session.flush()

        # Bulk upsert both existing and new words
        rows = [
            {
                "user_id": test_user_id,
                "language_id": test_language_id,
                "word": "python",
                "lemma": "python",
                "pos": "NOUN",
                "reading": "",
            },
            {
                "user_id": test_user_id,
                "language_id": test_language_id,
                "word": "javascript",
                "lemma": "javascript",
                "pos": "NOUN",
                "reading": "",
            },
        ]

        await word_repo.bulk_upsert(test_session, test_user_id, test_language_id, rows)
        await test_session.flush()

        # Verify: python keeps 'known', javascript is 'new'
        import sqlalchemy as sa

        result = await test_session.execute(
            sa.select(Word)
            .where(
                Word.user_id == test_user_id,
                Word.language_id == test_language_id,
            )
            .order_by(Word.word)
        )
        words = {w.word: w.status for w in result.scalars().all()}
        assert words["python"] == "known"
        assert words["javascript"] == "new"


class TestWordRepositoryGetWordsMap:
    """Test WordRepository.get_words_map()."""

    @pytest.mark.asyncio
    async def test_get_words_map_empty_words(
        self,
        test_session: AsyncSession,
        word_repo: WordRepository,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test get_words_map with empty word list."""
        result = await word_repo.get_words_map(
            test_session, test_user_id, test_language_id, []
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_words_map_retrieves_full_data(
        self,
        test_session: AsyncSession,
        word_repo: WordRepository,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test get_words_map returns full word metadata."""
        word1 = Word(
            user_id=test_user_id,
            language_id=test_language_id,
            word="hello",
            lemma="hello",
            pos="INTJ",
            reading="",
            gender="",
            status="new",
        )
        word2 = Word(
            user_id=test_user_id,
            language_id=test_language_id,
            word="world",
            lemma="world",
            pos="NOUN",
            reading="",
            gender="Neut",
            status="learning",
        )
        test_session.add_all([word1, word2])
        await test_session.flush()

        result = await word_repo.get_words_map(
            test_session,
            test_user_id,
            test_language_id,
            ["hello", "world"],
        )

        assert result["hello"]["status"] == "new"
        assert result["hello"]["pos"] == "INTJ"
        assert result["world"]["status"] == "learning"
        assert result["world"]["gender"] == "Neut"

    @pytest.mark.asyncio
    async def test_get_words_map_ignores_missing_words(
        self,
        test_session: AsyncSession,
        word_repo: WordRepository,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test get_words_map returns only existing words."""
        word1 = Word(
            user_id=test_user_id,
            language_id=test_language_id,
            word="hello",
            status="new",
        )
        test_session.add(word1)
        await test_session.flush()

        result = await word_repo.get_words_map(
            test_session,
            test_user_id,
            test_language_id,
            ["hello", "nonexistent", "alsomissing"],
        )

        assert "hello" in result
        assert "nonexistent" not in result

    @pytest.mark.asyncio
    async def test_get_words_map_includes_id(
        self,
        test_session: AsyncSession,
        word_repo: WordRepository,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """get_words_map must include the Word.id UUID string in each entry."""
        word = Word(
            user_id=test_user_id,
            language_id=test_language_id,
            word="kotlin",
            lemma="kotlin",
            pos="NOUN",
            reading="",
            gender="",
            status="learning",
        )
        test_session.add(word)
        await test_session.flush()

        result = await word_repo.get_words_map(
            test_session, test_user_id, test_language_id, ["kotlin"]
        )

        assert "kotlin" in result
        assert result["kotlin"]["id"] == str(word.id)

    @pytest.mark.asyncio
    async def test_get_words_map_respects_user_and_language(
        self,
        test_session: AsyncSession,
        word_repo: WordRepository,
        test_user_id: uuid.UUID,
        test_language_id: int,
    ):
        """Test that get_words_map only returns words for the specific user/language."""
        other_user = User(
            email=f"other-{uuid.uuid4().hex[:8]}@example.com",
            username=f"otherword-{uuid.uuid4().hex[:8]}",
            password_hash="hashed",
        )
        test_session.add(other_user)
        await test_session.flush()

        word1 = Word(
            user_id=test_user_id,
            language_id=test_language_id,
            word="hello",
            status="new",
        )
        word2 = Word(
            user_id=other_user.id,
            language_id=test_language_id,
            word="hello",
            status="known",
        )
        test_session.add_all([word1, word2])
        await test_session.flush()

        result = await word_repo.get_words_map(
            test_session,
            test_user_id,
            test_language_id,
            ["hello"],
        )

        assert result["hello"]["status"] == "new"
