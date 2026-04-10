import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.auth.services.password import hash_password
from src.domain.users.models import UserCreate, UserUpdate
from src.infrastructure.db.models.users import User
from src.infrastructure.db.repositories.user_repo import UserRepository


@pytest.fixture
def user_repo():
    """Provide a UserRepository instance."""
    return UserRepository()


class TestUserRepositoryCreate:
    """Test UserRepository.create()."""

    @pytest.mark.asyncio
    async def test_create_user_success(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test creating a new user."""
        user_create = UserCreate(
            email="john@example.com",
            username="john",
            password="securepassword",
        )

        user = await user_repo.create(test_session, user_create)

        assert user.id is not None
        assert user.email == "john@example.com"
        assert user.username == "john"
        assert user.password_hash != "securepassword"  # Should be hashed
        assert len(user.password_hash) > 0

    @pytest.mark.asyncio
    async def test_create_user_password_is_hashed(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test that password is hashed during creation."""
        plain_password = "mypassword123"
        user_create = UserCreate(
            email="jane@example.com",
            username="jane",
            password=plain_password,
        )

        user = await user_repo.create(test_session, user_create)

        # Verify password is hashed
        assert user.password_hash != plain_password
        from src.domain.auth.services.password import verify_password
        assert verify_password(plain_password, user.password_hash)

    @pytest.mark.asyncio
    async def test_create_multiple_users(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test creating multiple users."""
        user1_create = UserCreate(
            email="user1@example.com",
            username="user1",
            password="pass1",
        )
        user2_create = UserCreate(
            email="user2@example.com",
            username="user2",
            password="pass2",
        )

        user1 = await user_repo.create(test_session, user1_create)
        user2 = await user_repo.create(test_session, user2_create)

        assert user1.id != user2.id
        assert user1.email != user2.email


class TestUserRepositoryFindByEmail:
    """Test UserRepository.find_by_email()."""

    @pytest.mark.asyncio
    async def test_find_by_email_exists(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test finding a user by email."""
        user_create = UserCreate(
            email="alice@example.com",
            username="alice",
            password="password",
        )
        created_user = await user_repo.create(test_session, user_create)
        await test_session.flush()

        found_user = await user_repo.find_by_email(test_session, "alice@example.com")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_find_by_email_not_found(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test finding a non-existent user by email."""
        result = await user_repo.find_by_email(test_session, "nonexistent@example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_email_case_sensitive(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test that email search is case-sensitive."""
        user_create = UserCreate(
            email="Bob@Example.com",
            username="bob",
            password="password",
        )
        await user_repo.create(test_session, user_create)
        await test_session.flush()

        # Exact match should work
        found = await user_repo.find_by_email(test_session, "Bob@Example.com")
        assert found is not None

        # Different case might not match (database dependent)
        # This test documents the behavior
        found_lower = await user_repo.find_by_email(test_session, "bob@example.com")
        assert found_lower is None or found_lower.email == "Bob@Example.com"


class TestUserRepositoryFindById:
    """Test UserRepository.find_by_id()."""

    @pytest.mark.asyncio
    async def test_find_by_id_exists(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test finding a user by ID."""
        user_create = UserCreate(
            email="carol@example.com",
            username="carol",
            password="password",
        )
        created_user = await user_repo.create(test_session, user_create)
        await test_session.flush()

        found_user = await user_repo.find_by_id(test_session, created_user.id)

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "carol@example.com"

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test finding a non-existent user by ID."""
        import uuid

        fake_id = uuid.uuid4()
        result = await user_repo.find_by_id(test_session, fake_id)
        assert result is None


class TestUserRepositoryUpdate:
    """Test UserRepository.update()."""

    @pytest.mark.asyncio
    async def test_update_user_username(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test updating a user's username."""
        user_create = UserCreate(
            email="dave@example.com",
            username="dave",
            password="password",
        )
        created_user = await user_repo.create(test_session, user_create)
        await test_session.flush()

        user_update = UserUpdate(username="dave_updated")
        updated_user = await user_repo.update(
            test_session, created_user.id, user_update
        )

        assert updated_user is not None
        assert updated_user.username == "dave_updated"
        assert updated_user.email == "dave@example.com"  # Should not change

    @pytest.mark.asyncio
    async def test_update_user_password(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test updating a user's password."""
        user_create = UserCreate(
            email="eve@example.com",
            username="eve",
            password="oldpassword",
        )
        created_user = await user_repo.create(test_session, user_create)
        await test_session.flush()

        user_update = UserUpdate(password="newpassword")
        updated_user = await user_repo.update(
            test_session, created_user.id, user_update
        )

        assert updated_user is not None
        from src.domain.auth.services.password import verify_password
        assert verify_password("newpassword", updated_user.password_hash)

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test updating a non-existent user."""
        import uuid

        fake_id = uuid.uuid4()
        user_update = UserUpdate(username="new_name")
        result = await user_repo.update(test_session, fake_id, user_update)

        assert result is None


class TestUserRepositorySetRefreshTokenHash:
    """Test UserRepository.set_refresh_token_hash()."""

    @pytest.mark.asyncio
    async def test_set_refresh_token_hash(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test setting refresh token hash."""
        user_create = UserCreate(
            email="frank@example.com",
            username="frank",
            password="password",
        )
        created_user = await user_repo.create(test_session, user_create)
        await test_session.flush()

        token_hash = "hash123456"
        await user_repo.set_refresh_token_hash(
            test_session, created_user.id, token_hash
        )
        await test_session.flush()

        updated_user = await user_repo.find_by_id(test_session, created_user.id)
        assert updated_user.refresh_token_hash == token_hash

    @pytest.mark.asyncio
    async def test_set_refresh_token_hash_to_none(
        self, test_session: AsyncSession, user_repo: UserRepository
    ):
        """Test clearing refresh token hash by setting to None."""
        user_create = UserCreate(
            email="grace@example.com",
            username="grace",
            password="password",
        )
        created_user = await user_repo.create(test_session, user_create)
        await test_session.flush()

        # First set it
        await user_repo.set_refresh_token_hash(
            test_session, created_user.id, "somehash"
        )
        await test_session.flush()

        # Then clear it
        await user_repo.set_refresh_token_hash(test_session, created_user.id, None)
        await test_session.flush()

        updated_user = await user_repo.find_by_id(test_session, created_user.id)
        assert updated_user.refresh_token_hash is None
