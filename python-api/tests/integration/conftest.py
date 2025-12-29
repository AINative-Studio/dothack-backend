"""
Integration Test Fixtures

Provides shared fixtures for API integration tests including:
- Test database/ZeroDB client setup
- Mock authentication tokens and users
- Test data factories (hackathons, teams, users, submissions)
- HTTP client with authentication helpers
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional
from unittest.mock import AsyncMock, Mock, patch

# Set environment variables BEFORE any imports
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("API_VERSION", "v1")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
os.environ.setdefault("ZERODB_API_KEY", "test_key")
os.environ.setdefault("ZERODB_PROJECT_ID", "test_project")
os.environ.setdefault("ZERODB_BASE_URL", "https://api.ainative.studio")
os.environ.setdefault("ZERODB_TIMEOUT", "30.0")

import pytest
from fastapi.testclient import TestClient

# Mock settings to work around type mismatch in config.py
# The Settings class has a bug where ALLOWED_ORIGINS field is str but validator returns list
from unittest.mock import MagicMock

mock_settings = MagicMock()
mock_settings.ENVIRONMENT = "test"
mock_settings.LOG_LEVEL = "INFO"
mock_settings.API_VERSION = "v1"
mock_settings.ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
mock_settings.HOST = "0.0.0.0"
mock_settings.PORT = 8000
mock_settings.ZERODB_API_KEY = "test_key"
mock_settings.ZERODB_PROJECT_ID = "test_project"
mock_settings.ZERODB_BASE_URL = "https://api.ainative.studio"
mock_settings.ZERODB_TIMEOUT = 30.0

sys.modules["config"] = MagicMock(settings=mock_settings)

from integrations.zerodb.client import ZeroDBClient


# ============================================================================
# Test Client Fixtures
# ============================================================================


@pytest.fixture
def client() -> TestClient:
    """
    Create FastAPI test client.

    Returns:
        TestClient instance for making HTTP requests
    """
    # Import app lazily to avoid circular dependencies
    from main import app

    return TestClient(app)


class AuthenticatedClient:
    """
    Test client wrapper with authentication helpers.

    Automatically adds authentication headers to requests.
    """

    def __init__(self, client: TestClient, user: Dict[str, Any]):
        self.client = client
        self.user = user
        self.token = f"test-token-{user['id']}"

    def get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """Get authentication headers for requests."""
        if api_key:
            return {"X-API-Key": api_key}
        return {"Authorization": f"Bearer {self.token}"}

    def get(self, url: str, **kwargs) -> Any:
        """Make authenticated GET request."""
        headers = kwargs.pop("headers", {})
        headers.update(self.get_headers())
        return self.client.get(url, headers=headers, **kwargs)

    def post(self, url: str, **kwargs) -> Any:
        """Make authenticated POST request."""
        headers = kwargs.pop("headers", {})
        headers.update(self.get_headers())
        return self.client.post(url, headers=headers, **kwargs)

    def patch(self, url: str, **kwargs) -> Any:
        """Make authenticated PATCH request."""
        headers = kwargs.pop("headers", {})
        headers.update(self.get_headers())
        return self.client.patch(url, headers=headers, **kwargs)

    def delete(self, url: str, **kwargs) -> Any:
        """Make authenticated DELETE request."""
        headers = kwargs.pop("headers", {})
        headers.update(self.get_headers())
        return self.client.delete(url, headers=headers, **kwargs)


@pytest.fixture
def authenticated_client(client: TestClient, test_user: Dict[str, Any]) -> AuthenticatedClient:
    """
    Create authenticated test client.

    Returns:
        AuthenticatedClient with test user credentials
    """
    return AuthenticatedClient(client, test_user)


# ============================================================================
# User Fixtures
# ============================================================================


@pytest.fixture
def test_user() -> Dict[str, Any]:
    """
    Create test user data.

    Returns:
        User dictionary with id, email, name, email_verified
    """
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User",
        "email_verified": True,
    }


@pytest.fixture
def test_organizer() -> Dict[str, Any]:
    """
    Create test organizer user.

    Returns:
        Organizer user dictionary
    """
    return {
        "id": str(uuid.uuid4()),
        "email": "organizer@example.com",
        "name": "Test Organizer",
        "email_verified": True,
    }


@pytest.fixture
def test_judge() -> Dict[str, Any]:
    """
    Create test judge user.

    Returns:
        Judge user dictionary
    """
    return {
        "id": str(uuid.uuid4()),
        "email": "judge@example.com",
        "name": "Test Judge",
        "email_verified": True,
    }


@pytest.fixture
def test_builder() -> Dict[str, Any]:
    """
    Create test builder user.

    Returns:
        Builder user dictionary
    """
    return {
        "id": str(uuid.uuid4()),
        "email": "builder@example.com",
        "name": "Test Builder",
        "email_verified": True,
    }


# ============================================================================
# Data Factory Fixtures
# ============================================================================


@pytest.fixture
def hackathon_factory():
    """
    Factory for creating test hackathon data.

    Returns:
        Function that creates hackathon dictionaries
    """

    def _create_hackathon(
        organizer_id: Optional[str] = None,
        status: str = "draft",
        **overrides,
    ) -> Dict[str, Any]:
        """
        Create hackathon data dictionary.

        Args:
            organizer_id: Optional organizer user ID
            status: Hackathon status
            **overrides: Override default values

        Returns:
            Hackathon data dictionary
        """
        default_data = {
            "name": "Test Hackathon 2025",
            "description": "A test hackathon for integration tests",
            "organizer_id": organizer_id or str(uuid.uuid4()),
            "start_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=32)).isoformat(),
            "location": "Virtual",
            "status": status,
            "max_participants": 100,
            "website_url": "https://test-hackathon.com",
            "prizes": {"first": "$5000", "second": "$2500"},
            "rules": "Standard hackathon rules apply",
        }
        default_data.update(overrides)
        return default_data

    return _create_hackathon


@pytest.fixture
def team_factory():
    """
    Factory for creating test team data.

    Returns:
        Function that creates team dictionaries
    """

    def _create_team(
        hackathon_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        **overrides,
    ) -> Dict[str, Any]:
        """
        Create team data dictionary.

        Args:
            hackathon_id: Optional hackathon ID
            lead_id: Optional team lead user ID
            **overrides: Override default values

        Returns:
            Team data dictionary
        """
        default_data = {
            "hackathon_id": hackathon_id or str(uuid.uuid4()),
            "name": "Test Team Alpha",
            "description": "A test team for integration tests",
            "lead_id": lead_id or str(uuid.uuid4()),
            "max_members": 5,
            "status": "FORMING",
        }
        default_data.update(overrides)
        return default_data

    return _create_team


@pytest.fixture
def submission_factory():
    """
    Factory for creating test submission data.

    Returns:
        Function that creates submission dictionaries
    """

    def _create_submission(
        hackathon_id: Optional[str] = None,
        team_id: Optional[str] = None,
        **overrides,
    ) -> Dict[str, Any]:
        """
        Create submission data dictionary.

        Args:
            hackathon_id: Optional hackathon ID
            team_id: Optional team ID
            **overrides: Override default values

        Returns:
            Submission data dictionary
        """
        default_data = {
            "hackathon_id": hackathon_id or str(uuid.uuid4()),
            "team_id": team_id or str(uuid.uuid4()),
            "title": "Test Submission",
            "description": "A test project submission",
            "repository_url": "https://github.com/test/project",
            "demo_url": "https://demo.test-project.com",
            "status": "DRAFT",
        }
        default_data.update(overrides)
        return default_data

    return _create_submission


@pytest.fixture
def score_factory():
    """
    Factory for creating test score data.

    Returns:
        Function that creates score dictionaries
    """

    def _create_score(
        submission_id: Optional[str] = None,
        judge_id: Optional[str] = None,
        **overrides,
    ) -> Dict[str, Any]:
        """
        Create score data dictionary.

        Args:
            submission_id: Optional submission ID
            judge_id: Optional judge user ID
            **overrides: Override default values

        Returns:
            Score data dictionary
        """
        default_data = {
            "submission_id": submission_id or str(uuid.uuid4()),
            "judge_id": judge_id or str(uuid.uuid4()),
            "hackathon_id": str(uuid.uuid4()),
            "rubric_id": str(uuid.uuid4()),
            "scores": {
                "innovation": 8.5,
                "technical": 9.0,
                "design": 7.5,
                "presentation": 8.0,
            },
            "total_score": 8.25,
            "feedback": "Great project with innovative approach",
        }
        default_data.update(overrides)
        return default_data

    return _create_score


# ============================================================================
# Mock ZeroDB Client
# ============================================================================


@pytest.fixture
def mock_zerodb_client():
    """
    Create mock ZeroDB client.

    Returns:
        Mock ZeroDBClient with common methods
    """
    mock_client = Mock(spec=ZeroDBClient)

    # Mock common methods
    mock_client.insert_rows = AsyncMock()
    mock_client.query_rows = AsyncMock()
    mock_client.update_rows = AsyncMock()
    mock_client.delete_rows = AsyncMock()

    # Default return values
    mock_client.insert_rows.return_value = {"success": True, "inserted_ids": [str(uuid.uuid4())]}
    mock_client.query_rows.return_value = {"rows": [], "total": 0}
    mock_client.update_rows.return_value = {"success": True, "updated_count": 1}
    mock_client.delete_rows.return_value = {"success": True, "deleted_count": 1}

    return mock_client


# ============================================================================
# Authentication Mocks
# ============================================================================


@pytest.fixture
def mock_auth(test_user: Dict[str, Any]):
    """
    Mock authentication dependency.

    Returns:
        Patch context manager for get_current_user
    """
    with patch("api.dependencies.get_current_user") as mock:
        mock.return_value = test_user
        yield mock


@pytest.fixture
def mock_auth_organizer(test_organizer: Dict[str, Any]):
    """
    Mock authentication for organizer.

    Returns:
        Patch context manager for get_current_user (organizer)
    """
    with patch("api.dependencies.get_current_user") as mock:
        mock.return_value = test_organizer
        yield mock


@pytest.fixture
def mock_auth_judge(test_judge: Dict[str, Any]):
    """
    Mock authentication for judge.

    Returns:
        Patch context manager for get_current_user (judge)
    """
    with patch("api.dependencies.get_current_user") as mock:
        mock.return_value = test_judge
        yield mock


# ============================================================================
# Complete Integration Test Context
# ============================================================================


@pytest.fixture
async def integration_context(
    client: TestClient,
    test_user: Dict[str, Any],
    test_organizer: Dict[str, Any],
    test_judge: Dict[str, Any],
    hackathon_factory,
    team_factory,
    submission_factory,
    score_factory,
    mock_zerodb_client,
):
    """
    Complete integration test context.

    Provides all fixtures needed for full integration tests.

    Returns:
        Dictionary with all test fixtures and helpers
    """
    return {
        "client": client,
        "users": {
            "user": test_user,
            "organizer": test_organizer,
            "judge": test_judge,
        },
        "factories": {
            "hackathon": hackathon_factory,
            "team": team_factory,
            "submission": submission_factory,
            "score": score_factory,
        },
        "zerodb": mock_zerodb_client,
    }


# ============================================================================
# Utility Helpers
# ============================================================================


@pytest.fixture
def assert_error_response():
    """
    Helper for asserting error response format.

    Returns:
        Function that validates error response structure
    """

    def _assert_error(response: Any, expected_status: int, expected_message_contains: Optional[str] = None):
        """
        Assert error response has correct format.

        Args:
            response: HTTP response object
            expected_status: Expected HTTP status code
            expected_message_contains: Optional string expected in error message
        """
        assert response.status_code == expected_status
        data = response.json()
        assert "error" in data or "detail" in data

        if expected_message_contains:
            error_msg = data.get("error", {}).get("message", "") or data.get("detail", "")
            assert expected_message_contains.lower() in str(error_msg).lower()

    return _assert_error


@pytest.fixture
def wait_for_async():
    """
    Helper for waiting on async operations in tests.

    Returns:
        Function that waits for async operation completion
    """
    import asyncio

    def _wait(coro):
        """Execute async coroutine and return result."""
        return asyncio.get_event_loop().run_until_complete(coro)

    return _wait
