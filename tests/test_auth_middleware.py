"""Tests for authentication middleware."""

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


class TestAuthMiddleware:
    """Tests for auth middleware (get_current_user dependency)."""

    def test_protected_route_without_session(self, client):
        """Protected route without session returns 401."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_protected_route_with_invalid_session(self, client):
        """Protected route with invalid session ID returns 401."""
        client.cookies.set("session_id", "not-a-valid-uuid")
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert "Invalid session" in response.json()["detail"]

    def test_protected_route_with_nonexistent_session(self, client, db):
        """Protected route with nonexistent session returns 401."""
        import uuid
        client.cookies.set("session_id", str(uuid.uuid4()))
        response = client.get("/api/auth/me")

        assert response.status_code == 401

    def test_protected_route_with_valid_session(self, client, db):
        """Protected route with valid session returns user data."""
        # Register to get a valid session
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "protected@example.com",
                "password": "SecurePassword123!",
            },
        )

        # Verify registration succeeded
        assert register_response.status_code == 201
        assert "session_id" in client.cookies

        # Access protected route - TestClient should maintain session
        response = client.get("/api/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "protected@example.com"
        assert "id" in data

    def test_protected_route_after_logout(self, client, db):
        """Protected route after logout returns 401."""
        # Register
        client.post(
            "/api/auth/register",
            json={
                "email": "afterlogout@example.com",
                "password": "SecurePassword123!",
            },
        )

        # Logout
        client.post("/api/auth/logout")

        # Try to access protected route
        response = client.get("/api/auth/me")

        assert response.status_code == 401
