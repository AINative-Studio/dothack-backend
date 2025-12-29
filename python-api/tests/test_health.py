"""
Tests for health check endpoint.

Following TDD approach - tests written before implementation.
"""

from datetime import datetime

import pytest


def test_health_endpoint_returns_200(client):
    """
    Test that the health endpoint returns a 200 OK status code.
    """
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_json(client):
    """
    Test that the health endpoint returns JSON content.
    """
    response = client.get("/health")
    assert response.headers["content-type"] == "application/json"


def test_health_endpoint_structure(client):
    """
    Test that the health endpoint returns the expected JSON structure.

    Expected response:
    {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00.000000"
    }
    """
    response = client.get("/health")
    data = response.json()

    # Check required fields exist
    assert "status" in data
    assert "timestamp" in data

    # Check field values
    assert data["status"] == "healthy"
    assert isinstance(data["timestamp"], str)

    # Verify timestamp is a valid ISO format datetime
    try:
        datetime.fromisoformat(data["timestamp"])
    except ValueError:
        pytest.fail("timestamp is not in valid ISO format")


def test_health_endpoint_timestamp_is_recent(client):
    """
    Test that the health endpoint timestamp is recent (within last 5 seconds).
    """
    before = datetime.utcnow()
    response = client.get("/health")
    after = datetime.utcnow()

    data = response.json()
    timestamp = datetime.fromisoformat(data["timestamp"])

    # Timestamp should be between before and after the request
    assert before <= timestamp <= after
