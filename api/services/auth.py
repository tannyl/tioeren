"""Authentication service for password hashing and verification."""

import hashlib
import bcrypt

# Password requirements from spec
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

# Bcrypt has a 72-byte limit, so we pre-hash longer passwords with SHA256
# This is a standard approach when using bcrypt with potentially long passwords
BCRYPT_MAX_BYTES = 72


class PasswordValidationError(Exception):
    """Raised when password doesn't meet requirements."""
    pass


def validate_password(password: str) -> None:
    """
    Validate password meets requirements.

    Args:
        password: Plain text password to validate

    Raises:
        PasswordValidationError: If password doesn't meet requirements
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordValidationError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordValidationError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters"
        )


def _prepare_password(password: str) -> bytes:
    """
    Prepare password for bcrypt hashing.

    Since bcrypt has a 72-byte limit, we pre-hash longer passwords with SHA256.
    This is a standard approach recommended when using bcrypt with long passwords.

    Args:
        password: Plain text password

    Returns:
        Password ready for bcrypt as bytes
    """
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > BCRYPT_MAX_BYTES:
        # Pre-hash with SHA256 for passwords that exceed bcrypt's limit
        # Use the hex digest as a string, then encode to bytes
        return hashlib.sha256(password_bytes).hexdigest().encode('utf-8')
    return password_bytes


def hash_password(password: str) -> str:
    """
    Hash a plain text password.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string

    Raises:
        PasswordValidationError: If password doesn't meet requirements
    """
    validate_password(password)
    prepared = _prepare_password(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(prepared, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored password hash

    Returns:
        True if password matches, False otherwise
    """
    prepared = _prepare_password(plain_password)
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(prepared, hashed_bytes)
