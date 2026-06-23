"""Tests for FastAPI routes."""

import pytest
from fastapi.testclient import TestClient

from api.routes import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_get_atm_not_found(client):
    """Test ATM endpoint when data not available."""
    response = client.get("/atm")
    assert response.status_code == 404
