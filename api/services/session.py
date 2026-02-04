"""Session management service."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as DBSession

from api.models.session import Session
from api.models.user import User


# Session configuration
SESSION_LIFETIME_DAYS = 30


def create_session(db: DBSession, user: User) -> Session:
    """
    Create a new session for a user.

    Args:
        db: Database session
        user: User to create session for

    Returns:
        Created session
    """
    now = datetime.now(timezone.utc)
    session = Session(
        user_id=user.id,
        expires_at=now + timedelta(days=SESSION_LIFETIME_DAYS),
        last_activity=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DBSession, session_id: uuid.UUID) -> Session | None:
    """
    Get a session by ID.

    Args:
        db: Database session
        session_id: Session UUID

    Returns:
        Session if found, None otherwise
    """
    return db.query(Session).filter(Session.id == session_id).first()


def validate_session(db: DBSession, session_id: uuid.UUID) -> Session | None:
    """
    Validate a session and update last activity (sliding expiration).

    Args:
        db: Database session
        session_id: Session UUID

    Returns:
        Valid session with updated expiration, or None if invalid/expired
    """
    session = get_session(db, session_id)
    if session is None:
        return None

    now = datetime.now(timezone.utc)

    # Check if expired
    if session.expires_at < now:
        # Delete expired session
        db.delete(session)
        db.commit()
        return None

    # Update last activity and extend expiration (sliding window)
    session.last_activity = now
    session.expires_at = now + timedelta(days=SESSION_LIFETIME_DAYS)
    db.commit()
    db.refresh(session)

    return session


def invalidate_session(db: DBSession, session_id: uuid.UUID) -> bool:
    """
    Invalidate (delete) a specific session.

    Args:
        db: Database session
        session_id: Session UUID

    Returns:
        True if session was deleted, False if not found
    """
    session = get_session(db, session_id)
    if session is None:
        return False

    db.delete(session)
    db.commit()
    return True


def invalidate_all_user_sessions(db: DBSession, user_id: uuid.UUID) -> int:
    """
    Invalidate all sessions for a user.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        Number of sessions deleted
    """
    result = db.query(Session).filter(Session.user_id == user_id).delete()
    db.commit()
    return result
