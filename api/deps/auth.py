"""Authentication dependencies for route protection."""

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps.database import get_db
from api.models.user import User
from api.services.session import validate_session


def get_current_user(
    session_id: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user.

    Validates the session from cookie and returns the associated user.
    Raises 401 if no valid session.

    Args:
        session_id: Session ID from cookie (optional)
        db: Database session

    Returns:
        Authenticated user

    Raises:
        HTTPException: 401 if not authenticated
    """
    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    # Validate session and get updated session (sliding expiration)
    session = validate_session(db, session_uuid)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )

    # Get user (should exist due to FK constraint, but check anyway)
    user = db.query(User).filter(
        User.id == session.user_id,
        User.deleted_at.is_(None),
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# Type alias for use in route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
