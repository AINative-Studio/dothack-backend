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
def mock_user():
    """Default mock authenticated user for testing."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "name": "Test User",
        "role": "ADMIN",
        "email_verified": True,
    }


@pytest.fixture
def authenticated_client(mock_user):
    """
    Create a test client with get_current_user dependency overridden.

    Uses FastAPI's dependency_overrides to properly bypass authentication.
    This is the correct way to mock auth in FastAPI - patching the module
    attribute does NOT work because Depends() captures the function object
    at route definition time.
    """
    from main import app
    from api.dependencies import get_current_user

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield TestClient(app)

    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_env(monkeypatch):
    """
    Set up mock environment variables for testing.
    """
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("API_VERSION", "v1")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
