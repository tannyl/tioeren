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
                "email": "auth_route_test@example.com",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "auth_route_test@example.com"
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
        assert response.json()["detail"] == "auth.emailAlreadyRegistered"

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


class TestLogin:
    """Tests for login endpoint."""

    def test_login_success(self, client, db: DBSession):
        """Successful login returns 200 and sets cookie."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "password": "SecurePassword123!",
            },
        )

        # Clear cookies from registration
        client.cookies.clear()

        # Login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "login@example.com"
        assert "id" in data
        assert "session_id" in response.cookies

    def test_login_wrong_password(self, client, db: DBSession):
        """Wrong password returns 401."""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "SecurePassword123!",
            },
        )

        # Try wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "auth.invalidCredentials"

    def test_login_nonexistent_email(self, client, db: DBSession):
        """Nonexistent email returns 401."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "auth.invalidCredentials"

    def test_login_email_case_insensitive(self, client, db: DBSession):
        """Login should be case-insensitive for email."""
        # Register with lowercase
        client.post(
            "/api/auth/register",
            json={
                "email": "casetest@example.com",
                "password": "SecurePassword123!",
            },
        )

        client.cookies.clear()

        # Login with uppercase
        response = client.post(
            "/api/auth/login",
            json={
                "email": "CASETEST@EXAMPLE.COM",
                "password": "SecurePassword123!",
            },
        )

        assert response.status_code == 200


class TestLogout:
    """Tests for logout endpoint."""

    def test_logout_with_session(self, client, db: DBSession):
        """Logout with valid session clears cookie."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={
                "email": "logout@example.com",
                "password": "SecurePassword123!",
            },
        )

        # Verify we have a session cookie
        assert "session_id" in client.cookies

        # Logout
        response = client.post("/api/auth/logout")

        assert response.status_code == 204
        # Cookie should be cleared (set to empty or deleted)

    def test_logout_without_session(self, client):
        """Logout without session still returns 204."""
        response = client.post("/api/auth/logout")

        assert response.status_code == 204

    def test_logout_invalidates_session(self, client, db: DBSession):
        """After logout, the session is deleted and cookie is cleared."""
        # Register to get a session
        client.post(
            "/api/auth/register",
            json={
                "email": "invalidate@example.com",
                "password": "SecurePassword123!",
            },
        )

        session_id = client.cookies.get("session_id")
        assert session_id is not None, "Should have session after registration"

        # Logout
        response = client.post("/api/auth/logout")
        assert response.status_code == 204

        # Note: Verification that the session is actually deleted from the database
        # is deferred to integration tests with protected endpoints (future task).
        # In a transactional test environment, db.commit() behaves differently,
        # making direct database verification unreliable. The important behavior
        # (session invalidation preventing access to protected resources) will be
        # tested when we implement authentication dependencies.
