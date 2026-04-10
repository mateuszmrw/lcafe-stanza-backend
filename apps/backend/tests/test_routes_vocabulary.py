"""
Tests for vocabulary routes:
  - GET  /vocabulary            (list, includes gender field)
  - GET  /vocabulary/{id}       (single word, includes gender)
  - PATCH /vocabulary/{id}/status
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.users.models import UserCreate
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.user_repo import UserRepository


@pytest.fixture
async def test_language(test_session: AsyncSession) -> Language:
    lang = Language(code="en", name="English")
    test_session.add(lang)
    await test_session.flush()
    await test_session.commit()
    return lang


@pytest.fixture
async def authenticated_user(test_session: AsyncSession, test_client: AsyncClient):
    repo = UserRepository()
    user = await repo.create(
        test_session,
        UserCreate(email="vocab@example.com", username="vocab", password="password123"),
    )
    await test_session.flush()
    await test_session.commit()

    login = await test_client.post(
        "/auth/login",
        json={"email": "vocab@example.com", "password": "password123"},
    )
    return user, login.json()["access_token"]


async def _add_word(
    session: AsyncSession,
    user_id: uuid.UUID,
    language_id: int,
    word: str = "hello",
    lemma: str = "hello",
    pos: str = "NOUN",
    gender: str = "Masc",
    status: str = "new",
) -> Word:
    w = Word(
        user_id=user_id,
        language_id=language_id,
        word=word,
        lemma=lemma,
        pos=pos,
        reading="",
        gender=gender,
        status=status,
    )
    session.add(w)
    await session.flush()
    await session.commit()
    return w


class TestListVocabulary:
    @pytest.mark.asyncio
    async def test_list_returns_words(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """GET /vocabulary returns words for the user and language."""
        user, access_token = authenticated_user
        await _add_word(test_session, user.id, test_language.id)

        response = await test_client.get(
            f"/vocabulary?language_id={test_language.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_includes_gender_field(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """WordResponse must expose the gender field."""
        user, access_token = authenticated_user
        await _add_word(test_session, user.id, test_language.id, gender="Fem")

        response = await test_client.get(
            f"/vocabulary?language_id={test_language.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert "gender" in item
        assert item["gender"] == "Fem"

    @pytest.mark.asyncio
    async def test_list_gender_empty_string_when_unset(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """gender defaults to empty string for words without gender data."""
        user, access_token = authenticated_user
        await _add_word(test_session, user.id, test_language.id, gender="")

        response = await test_client.get(
            f"/vocabulary?language_id={test_language.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["gender"] == ""

    @pytest.mark.asyncio
    async def test_list_status_filter(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """?status=learning returns only words with that status."""
        user, access_token = authenticated_user
        await _add_word(test_session, user.id, test_language.id, word="one", status="learning")
        await _add_word(test_session, user.id, test_language.id, word="two", status="known")

        response = await test_client.get(
            f"/vocabulary?language_id={test_language.id}&status=learning",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["word"] == "one"

    @pytest.mark.asyncio
    async def test_list_pagination(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """page/limit pagination works correctly."""
        user, access_token = authenticated_user
        for i in range(5):
            await _add_word(test_session, user.id, test_language.id, word=f"word{i}")

        response = await test_client.get(
            f"/vocabulary?language_id={test_language.id}&page=1&limit=3",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["limit"] == 3

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, test_client: AsyncClient, test_language: Language):
        response = await test_client.get(f"/vocabulary?language_id={test_language.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_does_not_return_other_users_words(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Words belonging to another user are not visible."""
        _, access_token = authenticated_user

        repo = UserRepository()
        other = await repo.create(
            test_session,
            UserCreate(email="other@vocab.com", username="othervocab", password="password123"),
        )
        await test_session.flush()
        await _add_word(test_session, other.id, test_language.id, word="secret")

        response = await test_client.get(
            f"/vocabulary?language_id={test_language.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestGetWord:
    @pytest.mark.asyncio
    async def test_get_single_word(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """GET /vocabulary/{id} returns the word with all fields."""
        user, access_token = authenticated_user
        word = await _add_word(
            test_session, user.id, test_language.id,
            word="rust", lemma="rust", gender="Neut", status="learning"
        )

        response = await test_client.get(
            f"/vocabulary/{word.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["word"] == "rust"
        assert data["gender"] == "Neut"
        assert data["status"] == "learning"
        assert data["id"] == str(word.id)

    @pytest.mark.asyncio
    async def test_get_word_not_found(
        self, test_client: AsyncClient, authenticated_user
    ):
        _, access_token = authenticated_user
        response = await test_client.get(
            f"/vocabulary/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_word_belonging_to_other_user_is_404(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        _, access_token = authenticated_user

        repo = UserRepository()
        other = await repo.create(
            test_session,
            UserCreate(email="gw_other@vocab.com", username="gwother", password="password123"),
        )
        await test_session.flush()
        word = await _add_word(test_session, other.id, test_language.id, word="secret2")

        response = await test_client.get(
            f"/vocabulary/{word.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404


class TestUpdateWordStatus:
    @pytest.mark.asyncio
    async def test_update_status(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """PATCH /vocabulary/{id}/status updates the word status."""
        user, access_token = authenticated_user
        word = await _add_word(test_session, user.id, test_language.id, status="new")

        response = await test_client.patch(
            f"/vocabulary/{word.id}/status",
            json={"status": "known"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "known"

    @pytest.mark.asyncio
    async def test_update_status_returns_gender(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """PATCH response includes the gender field."""
        user, access_token = authenticated_user
        word = await _add_word(
            test_session, user.id, test_language.id,
            word="der", gender="Masc", status="new"
        )

        response = await test_client.patch(
            f"/vocabulary/{word.id}/status",
            json={"status": "learning"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json()["gender"] == "Masc"

    @pytest.mark.asyncio
    async def test_update_status_not_found(
        self, test_client: AsyncClient, authenticated_user
    ):
        _, access_token = authenticated_user
        response = await test_client.patch(
            f"/vocabulary/{uuid.uuid4()}/status",
            json={"status": "known"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_status_other_users_word_is_404(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        _, access_token = authenticated_user

        repo = UserRepository()
        other = await repo.create(
            test_session,
            UserCreate(email="us_other@vocab.com", username="usother", password="password123"),
        )
        await test_session.flush()
        word = await _add_word(test_session, other.id, test_language.id, word="forbidden")

        response = await test_client.patch(
            f"/vocabulary/{word.id}/status",
            json={"status": "known"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404
