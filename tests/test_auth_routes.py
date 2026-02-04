"""Tests for authentication routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as DBSession

from api.main import app
from api.deps.database import get_db


@pytest.fixture
def client(db: DBSession):
    """Create test client with overridden database dependency."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestRegister:
    """Tests for registration endpoint."""

    def test_register_success(self, client, db: DBSession):
        """Successful registration returns 201 and sets cookie."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert data["message"] == "Registration successful"
        assert "session_id" in response.cookies

    def test_register_duplicate_email(self, client, db: DBSession):
        """Duplicate email returns 409."""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePassword123!",
            },
        )

        # Try to register with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "AnotherPassword123!",
            },
        )

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Invalid email returns 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 422

    def test_register_password_too_short(self, client):
        """Short password returns 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
            },
        )

        assert response.status_code == 422

    def test_register_email_case_insensitive(self, client, db: DBSession):
        """Email should be case-insensitive."""
        # Register with uppercase
        client.post(
            "/api/auth/register",
            json={
                "email": "Test@Example.COM",
                "password": "SecurePassword123!",
            },
        )

        # Try lowercase
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "AnotherPassword123!",
            },
        )

        assert response.status_code == 409
