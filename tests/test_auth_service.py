"""Tests for authentication service."""

import pytest

from api.services.auth import (
    hash_password,
    verify_password,
    validate_password,
    PasswordValidationError,
    MIN_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
)


class TestPasswordValidation:
    """Tests for password validation."""

    def test_valid_password(self):
        """Valid password should not raise."""
        validate_password("a" * MIN_PASSWORD_LENGTH)
        validate_password("a" * MAX_PASSWORD_LENGTH)
        validate_password("SecurePassword123!")

    def test_password_too_short(self):
        """Password shorter than minimum should raise."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password("a" * (MIN_PASSWORD_LENGTH - 1))
        assert f"at least {MIN_PASSWORD_LENGTH}" in str(exc_info.value)

    def test_password_too_long(self):
        """Password longer than maximum should raise."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password("a" * (MAX_PASSWORD_LENGTH + 1))
        assert f"at most {MAX_PASSWORD_LENGTH}" in str(exc_info.value)


class TestPasswordHashing:
    """Tests for password hashing."""

    def test_hash_returns_string(self):
        """Hash should return a string."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert hashed != password

    def test_hash_is_bcrypt_format(self):
        """Hash should be in bcrypt format."""
        hashed = hash_password("SecurePassword123!")
        assert hashed.startswith("$2b$")

    def test_same_password_different_hash(self):
        """Same password should produce different hashes (salt)."""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_hash_validates_password(self):
        """Hash should validate password requirements."""
        with pytest.raises(PasswordValidationError):
            hash_password("short")


class TestPasswordVerification:
    """Tests for password verification."""

    def test_verify_correct_password(self):
        """Correct password should verify."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password should not verify."""
        hashed = hash_password("SecurePassword123!")
        assert verify_password("WrongPassword123!", hashed) is False

    def test_verify_similar_password(self):
        """Similar but different password should not verify."""
        hashed = hash_password("SecurePassword123!")
        assert verify_password("SecurePassword123", hashed) is False
