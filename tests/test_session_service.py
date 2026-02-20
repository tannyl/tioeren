"""Tests for session service."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session as DBSession

from api.models.user import User
from api.models.session import Session
from api.services.session import (
    create_session,
    get_session,
    validate_session,
    invalidate_session,
    invalidate_all_user_sessions,
    SESSION_LIFETIME_DAYS,
)


@pytest.fixture
def test_user(db: DBSession) -> User:
    """Create a test user."""
    user = User(
        email="session_test@example.com",
        password_hash="dummy_hash",
        email_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_session(db: DBSession, test_user: User):
    """Test session creation."""
    session = create_session(db, test_user)

    assert session.id is not None
    assert session.user_id == test_user.id
    assert session.created_at is not None
    assert session.expires_at is not None
    assert session.last_activity is not None

    # Check expiration is set correctly (30 days from now)
    expected_expiration = session.created_at + timedelta(days=SESSION_LIFETIME_DAYS)
    assert abs((session.expires_at - expected_expiration).total_seconds()) < 2


def test_get_session(db: DBSession, test_user: User):
    """Test getting a session by ID."""
    session = create_session(db, test_user)

    retrieved = get_session(db, session.id)
    assert retrieved is not None
    assert retrieved.id == session.id
    assert retrieved.user_id == test_user.id


def test_get_session_not_found(db: DBSession):
    """Test getting a non-existent session returns None."""
    non_existent_id = uuid.uuid4()
    result = get_session(db, non_existent_id)
    assert result is None


def test_validate_session_valid(db: DBSession, test_user: User):
    """Test validating a valid session."""
    session = create_session(db, test_user)
    original_expiration = session.expires_at

    # Small delay to ensure time difference
    import time
    time.sleep(0.1)

    validated = validate_session(db, session.id)

    assert validated is not None
    assert validated.id == session.id
    # Expiration should be extended (sliding window)
    assert validated.expires_at > original_expiration


def test_validate_session_expired(db: DBSession, test_user: User):
    """Test validating an expired session returns None and deletes it."""
    session = create_session(db, test_user)

    # Manually set expiration to the past
    session.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()

    validated = validate_session(db, session.id)

    assert validated is None

    # Session should be deleted from database
    deleted = get_session(db, session.id)
    assert deleted is None


def test_validate_session_not_found(db: DBSession):
    """Test validating a non-existent session returns None."""
    non_existent_id = uuid.uuid4()
    result = validate_session(db, non_existent_id)
    assert result is None


def test_invalidate_session(db: DBSession, test_user: User):
    """Test invalidating a session."""
    session = create_session(db, test_user)

    result = invalidate_session(db, session.id)
    assert result is True

    # Session should be deleted
    deleted = get_session(db, session.id)
    assert deleted is None


def test_invalidate_session_not_found(db: DBSession):
    """Test invalidating a non-existent session returns False."""
    non_existent_id = uuid.uuid4()
    result = invalidate_session(db, non_existent_id)
    assert result is False


def test_invalidate_all_user_sessions(db: DBSession, test_user: User):
    """Test invalidating all sessions for a user."""
    # Create multiple sessions and store their IDs
    session1 = create_session(db, test_user)
    session2 = create_session(db, test_user)
    session3 = create_session(db, test_user)

    # Store IDs before deletion (to avoid SQLAlchemy trying to refresh deleted objects)
    session1_id = session1.id
    session2_id = session2.id
    session3_id = session3.id

    count = invalidate_all_user_sessions(db, test_user.id)
    assert count == 3

    # All sessions should be deleted
    assert get_session(db, session1_id) is None
    assert get_session(db, session2_id) is None
    assert get_session(db, session3_id) is None


def test_invalidate_all_user_sessions_no_sessions(db: DBSession, test_user: User):
    """Test invalidating sessions when user has none returns 0."""
    count = invalidate_all_user_sessions(db, test_user.id)
    assert count == 0


def test_sliding_expiration(db: DBSession, test_user: User):
    """Test that session extends on activity (sliding expiration)."""
    session = create_session(db, test_user)
    original_expiration = session.expires_at

    # Simulate some delay
    import time
    time.sleep(0.1)

    # Validate extends expiration
    validated = validate_session(db, session.id)
    assert validated is not None

    new_expiration = validated.expires_at
    assert new_expiration > original_expiration

    # Check that new expiration is approximately 30 days from now
    expected = datetime.now(timezone.utc) + timedelta(days=SESSION_LIFETIME_DAYS)
    assert abs((new_expiration - expected).total_seconds()) < 2


def test_cascade_delete_user_deletes_sessions(db: DBSession, test_user: User):
    """Test that deleting a user cascades to delete all their sessions."""
    session1 = create_session(db, test_user)
    session2 = create_session(db, test_user)

    # Store IDs before deletion
    session1_id = session1.id
    session2_id = session2.id

    # Delete the user
    db.delete(test_user)
    db.commit()

    # Sessions should be automatically deleted due to CASCADE
    assert get_session(db, session1_id) is None
    assert get_session(db, session2_id) is None
