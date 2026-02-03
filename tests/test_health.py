"""Tests for health check endpoint."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_check():
    """Test that health endpoint returns OK."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
