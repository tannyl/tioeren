"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field

from api.services.auth import MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH


class UserRegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
    )


class UserRegisterResponse(BaseModel):
    """Response body for successful registration."""

    id: str
    email: str
    message: str = "Registration successful"


class AuthErrorResponse(BaseModel):
    """Error response for auth endpoints."""

    detail: str
