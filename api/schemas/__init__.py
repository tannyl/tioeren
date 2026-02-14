"""Pydantic schemas for request/response validation."""

# PostgreSQL BIGINT max value — shared across all schema files
MAX_BIGINT = 9_223_372_036_854_775_807

from api.schemas.auth import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserLoginResponse,
    AuthErrorResponse,
)

__all__ = [
    "UserRegisterRequest",
    "UserRegisterResponse",
    "UserLoginRequest",
    "UserLoginResponse",
    "AuthErrorResponse",
]
