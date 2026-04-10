import pytest

from src.domain.auth.services.password import hash_password, verify_password


class TestHashPassword:
    """Test password hashing functionality."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        plain = "mypassword123"
        hashed = hash_password(plain)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_produces_different_hashes(self):
        """Test that same password produces different hashes due to salt."""
        plain = "mypassword123"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert hash1 != hash2  # Different salts

    def test_hash_password_with_empty_string(self):
        """Test hashing an empty password."""
        plain = ""
        hashed = hash_password(plain)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_with_special_characters(self):
        """Test hashing password with special characters."""
        plain = "p@ssw0rd!#$%"
        hashed = hash_password(plain)
        assert isinstance(hashed, str)
        assert len(hashed) > 0


class TestVerifyPassword:
    """Test password verification functionality."""

    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        plain = "mypassword123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        plain = "mypassword123"
        hashed = hash_password(plain)
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        plain = "MyPassword"
        hashed = hash_password(plain)
        assert verify_password("mypassword", hashed) is False
        assert verify_password("MyPassword", hashed) is True

    def test_verify_password_empty_password(self):
        """Test verification with empty password."""
        plain = ""
        hashed = hash_password(plain)
        assert verify_password("", hashed) is True
        assert verify_password("notEmpty", hashed) is False

    def test_verify_password_with_special_characters(self):
        """Test verification with special characters."""
        plain = "p@ssw0rd!#$%"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True
        assert verify_password("p@ssw0rd!#", hashed) is False
