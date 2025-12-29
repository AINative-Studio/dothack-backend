"""
Pytest configuration and fixtures for FastAPI testing.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.

    This fixture is imported late to avoid circular dependencies
    and to ensure the app is properly configured before testing.
    """
    from main import app

    return TestClient(app)


@pytest.fixture
def mock_env(monkeypatch):
    """
    Set up mock environment variables for testing.
    """
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("API_VERSION", "v1")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
