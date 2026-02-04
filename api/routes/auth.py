"""Authentication routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from api.deps.database import get_db
from api.deps.auth import CurrentUser
from api.deps.config import settings
from api.models.user import User
from api.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserLoginResponse,
)
from api.services.auth import hash_password, verify_password, PasswordValidationError
from api.services.session import create_session, invalidate_session


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation error"},
    },
)
def register(
    request: UserRegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserRegisterResponse:
    """
    Register a new user.

    Creates a new user account and returns a session cookie.
    Email verification is stubbed for MVP.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(
        User.email == request.email.lower(),
        User.deleted_at.is_(None),
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash password
    try:
        password_hash = hash_password(request.password)
    except PasswordValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Create user
    user = User(
        email=request.email.lower(),
        password_hash=password_hash,
        email_verified=True,  # Stubbed for MVP
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create session
    session = create_session(db, user)

    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=str(session.id),
        httponly=True,
        secure=not settings.TESTING,  # Disable secure flag in tests
        samesite="strict",
        max_age=30 * 24 * 60 * 60,  # 30 days
    )

    return UserRegisterResponse(
        id=str(user.id),
        email=user.email,
    )


@router.post(
    "/login",
    response_model=UserLoginResponse,
    responses={
        401: {"description": "Invalid credentials"},
    },
)
def login(
    request: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserLoginResponse:
    """
    Login with email and password.

    Verifies credentials and returns a session cookie.
    """
    # Find user by email (case-insensitive)
    user = db.query(User).filter(
        User.email == request.email.lower(),
        User.deleted_at.is_(None),
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create session
    session = create_session(db, user)

    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=str(session.id),
        httponly=True,
        secure=not settings.TESTING,  # Disable secure flag in tests
        samesite="strict",
        max_age=30 * 24 * 60 * 60,  # 30 days
    )

    return UserLoginResponse(
        id=str(user.id),
        email=user.email,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """
    Logout the current user.

    Invalidates the current session and clears the cookie.
    """
    # Get session ID from cookie
    session_id = request.cookies.get("session_id")

    if session_id:
        try:
            session_uuid = uuid.UUID(session_id)
            invalidate_session(db, session_uuid)
        except ValueError:
            # Invalid UUID format, just clear the cookie
            pass

    # Clear the cookie
    response.delete_cookie(
        key="session_id",
        httponly=True,
        secure=not settings.TESTING,  # Match secure flag from set_cookie
        samesite="strict",
    )


@router.get("/me")
def get_current_user_info(
    current_user: CurrentUser,
) -> dict:
    """
    Get current user information.

    Protected endpoint that requires authentication.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
    }
