"""
Task 10: Test that GET /books/{id}/pages returns tokens with non-null `id`
field when words exist in the Word table.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.content import ContentItem, ContentPage
from src.infrastructure.db.models.languages import Language
from src.infrastructure.db.models.words import Word
from src.infrastructure.db.repositories.user_repo import UserRepository
from src.domain.users.models import UserCreate


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
        UserCreate(email="wordid@example.com", username="wordid", password="password123"),
    )
    await test_session.flush()
    await test_session.commit()

    login = await test_client.post(
        "/auth/login",
        json={"email": "wordid@example.com", "password": "password123"},
    )
    return user, login.json()["access_token"]


class TestTokenWordId:
    @pytest.mark.asyncio
    async def test_tokens_include_word_id_for_known_words(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Tokens for words in the Word table must have a non-null `id` field."""
        user, access_token = authenticated_user
        lang_id = test_language.id

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=lang_id,
            type="book",
            title="Word ID Test Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        page = ContentPage(
            content_item_id=content_item.id,
            page_number=1,
            text="hello world python",
            status="ready",
        )
        test_session.add(page)
        await test_session.flush()

        word = Word(
            user_id=user.id,
            language_id=lang_id,
            word="hello",
            lemma="hello",
            pos="INTJ",
            reading="",
            gender="",
            status="learning",
        )
        test_session.add(word)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.get(
            f"/books/{content_item.id}/pages",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        tokens = response.json()["items"][0]["tokens"]
        token_map = {t["w"].lower(): t for t in tokens}

        # "hello" is in Word table — must have a string UUID
        assert token_map["hello"]["id"] is not None
        assert token_map["hello"]["id"] == str(word.id)

        # "world" and "python" are unknown — id should be null/absent
        assert token_map["world"].get("id") is None
        assert token_map["python"].get("id") is None

    @pytest.mark.asyncio
    async def test_tokens_id_none_when_no_word_entry(
        self,
        test_session: AsyncSession,
        test_client: AsyncClient,
        authenticated_user,
        test_language: Language,
    ):
        """Tokens for words NOT in the Word table must have id=null."""
        user, access_token = authenticated_user
        lang_id = test_language.id

        content_item = ContentItem(
            id=uuid.uuid4(),
            user_id=user.id,
            language_id=lang_id,
            type="book",
            title="No Vocab Book",
            status="completed",
        )
        test_session.add(content_item)
        await test_session.flush()

        page = ContentPage(
            content_item_id=content_item.id,
            page_number=1,
            text="unknown words here",
            status="ready",
        )
        test_session.add(page)
        await test_session.flush()
        await test_session.commit()

        response = await test_client.get(
            f"/books/{content_item.id}/pages",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        tokens = response.json()["items"][0]["tokens"]
        for token in tokens:
            assert token.get("id") is None
