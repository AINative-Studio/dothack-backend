"""
Tests for Dashboard API Endpoints

Tests all role-based dashboard endpoints for organizers, builders, and judges.
Uses TestClient for integration testing with mocked dependencies.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from api.routes.dashboard import get_current_user, get_zerodb_client, router
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound


# Create test app with dashboard router
app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_organizer_user():
    """Mock organizer user"""
    return {
        "id": str(uuid.uuid4()),
        "email": "organizer@example.com",
        "name": "Test Organizer",
        "role": "ORGANIZER",
    }


@pytest.fixture
def mock_builder_user():
    """Mock builder user"""
    return {
        "id": str(uuid.uuid4()),
        "email": "builder@example.com",
        "name": "Test Builder",
        "role": "BUILDER",
    }


@pytest.fixture
def mock_judge_user():
    """Mock judge user"""
    return {
        "id": str(uuid.uuid4()),
        "email": "judge@example.com",
        "name": "Test Judge",
        "role": "JUDGE",
    }


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client"""
    return AsyncMock()


@pytest.fixture
def organizer_client(mock_organizer_user, mock_zerodb_client):
    """Test client with organizer user"""

    async def override_get_current_user():
        return mock_organizer_user

    async def override_get_zerodb_client():
        return mock_zerodb_client

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_zerodb_client] = override_get_zerodb_client

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def builder_client(mock_builder_user, mock_zerodb_client):
    """Test client with builder user"""

    async def override_get_current_user():
        return mock_builder_user

    async def override_get_zerodb_client():
        return mock_zerodb_client

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_zerodb_client] = override_get_zerodb_client

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def judge_client(mock_judge_user, mock_zerodb_client):
    """Test client with judge user"""

    async def override_get_current_user():
        return mock_judge_user

    async def override_get_zerodb_client():
        return mock_zerodb_client

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_zerodb_client] = override_get_zerodb_client

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


class TestOrganizerDashboardEndpoint:
    """Test GET /dashboard/organizer - Organizer dashboard"""

    @patch("api.routes.dashboard.dashboard_service.get_organizer_dashboard")
    def test_get_organizer_dashboard_success(
        self, mock_get_dashboard, organizer_client, mock_organizer_user
    ):
        """Should return organizer dashboard with statistics"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        mock_get_dashboard.return_value = {
            "hackathons": [
                {
                    "hackathon_id": hackathon_id,
                    "name": "Test Hackathon",
                    "status": "ACTIVE",
                    "participant_count": 50,
                    "team_count": 10,
                    "submission_count": 8,
                }
            ],
            "total_hackathons": 1,
            "total_participants": 50,
            "total_teams": 10,
            "total_submissions": 8,
            "pending_judgments": 8,
            "recent_activity": [
                {
                    "activity_type": "submission",
                    "description": "New submission received",
                    "timestamp": "2024-01-01T12:00:00",
                }
            ],
        }

        # Act
        response = organizer_client.get("/api/v1/dashboard/organizer")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_hackathons"] == 1
        assert data["total_participants"] == 50
        assert data["total_teams"] == 10
        assert data["total_submissions"] == 8
        assert data["pending_judgments"] == 8
        assert len(data["hackathons"]) == 1
        assert len(data["recent_activity"]) == 1

    @patch("api.routes.dashboard.dashboard_service.get_organizer_dashboard")
    def test_get_organizer_dashboard_empty(
        self, mock_get_dashboard, organizer_client
    ):
        """Should return empty dashboard when no hackathons organized"""
        # Arrange
        mock_get_dashboard.return_value = {
            "hackathons": [],
            "total_hackathons": 0,
            "total_participants": 0,
            "total_teams": 0,
            "total_submissions": 0,
            "pending_judgments": 0,
            "recent_activity": [],
        }

        # Act
        response = organizer_client.get("/api/v1/dashboard/organizer")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_hackathons"] == 0
        assert len(data["hackathons"]) == 0


class TestBuilderDashboardEndpoint:
    """Test GET /dashboard/builder - Builder dashboard"""

    @patch("api.routes.dashboard.dashboard_service.get_builder_dashboard")
    def test_get_builder_dashboard_success(
        self, mock_get_dashboard, builder_client, mock_builder_user
    ):
        """Should return builder dashboard with participation info"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        team_id = str(uuid.uuid4())

        mock_get_dashboard.return_value = {
            "registered_hackathons": [
                {
                    "hackathon_id": hackathon_id,
                    "name": "Test Hackathon",
                    "status": "ACTIVE",
                    "registration_date": "2024-01-01T00:00:00",
                }
            ],
            "teams": [
                {
                    "team_id": team_id,
                    "name": "My Team",
                    "hackathon_id": hackathon_id,
                    "role": "MEMBER",
                }
            ],
            "submissions": [
                {
                    "submission_id": str(uuid.uuid4()),
                    "title": "My Project",
                    "team_id": team_id,
                    "status": "SUBMITTED",
                }
            ],
            "upcoming_deadlines": [
                {
                    "hackathon_name": "Test Hackathon",
                    "deadline_type": "submission",
                    "deadline": "2024-12-31T23:59:59",
                }
            ],
        }

        # Act
        response = builder_client.get("/api/v1/dashboard/builder")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["registered_hackathons"]) == 1
        assert len(data["teams"]) == 1
        assert len(data["submissions"]) == 1
        assert len(data["upcoming_deadlines"]) == 1

    @patch("api.routes.dashboard.dashboard_service.get_builder_dashboard")
    def test_get_builder_dashboard_empty(self, mock_get_dashboard, builder_client):
        """Should return empty dashboard when no participation"""
        # Arrange
        mock_get_dashboard.return_value = {
            "registered_hackathons": [],
            "teams": [],
            "submissions": [],
            "upcoming_deadlines": [],
        }

        # Act
        response = builder_client.get("/api/v1/dashboard/builder")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["registered_hackathons"]) == 0
        assert len(data["teams"]) == 0


class TestJudgeDashboardEndpoint:
    """Test GET /dashboard/judge - Judge dashboard"""

    @patch("api.routes.dashboard.dashboard_service.get_judge_dashboard")
    def test_get_judge_dashboard_success(
        self, mock_get_dashboard, judge_client, mock_judge_user
    ):
        """Should return judge dashboard with judging assignments"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        mock_get_dashboard.return_value = {
            "assigned_hackathons": [
                {
                    "hackathon_id": hackathon_id,
                    "name": "Test Hackathon",
                    "status": "ACTIVE",
                }
            ],
            "submissions_to_judge": [
                {
                    "submission_id": str(uuid.uuid4()),
                    "title": "Project to Judge",
                    "hackathon_id": hackathon_id,
                    "status": "PENDING_REVIEW",
                }
            ],
            "completed_judgments": 5,
            "pending_judgments": 3,
            "total_assigned": 8,
        }

        # Act
        response = judge_client.get("/api/v1/dashboard/judge")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["assigned_hackathons"]) == 1
        assert len(data["submissions_to_judge"]) == 1
        assert data["completed_judgments"] == 5
        assert data["pending_judgments"] == 3
        assert data["total_assigned"] == 8

    @patch("api.routes.dashboard.dashboard_service.get_judge_dashboard")
    def test_get_judge_dashboard_empty(self, mock_get_dashboard, judge_client):
        """Should return empty dashboard when no assignments"""
        # Arrange
        mock_get_dashboard.return_value = {
            "assigned_hackathons": [],
            "submissions_to_judge": [],
            "completed_judgments": 0,
            "pending_judgments": 0,
            "total_assigned": 0,
        }

        # Act
        response = judge_client.get("/api/v1/dashboard/judge")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["assigned_hackathons"]) == 0
        assert data["completed_judgments"] == 0


class TestHackathonOverviewEndpoint:
    """Test GET /dashboard/hackathons/{hackathon_id} - Hackathon overview"""

    @patch("api.routes.dashboard.dashboard_service.get_hackathon_overview")
    def test_get_hackathon_overview_success(
        self, mock_get_overview, organizer_client, mock_organizer_user
    ):
        """Should return comprehensive hackathon overview"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        mock_get_overview.return_value = {
            "hackathon": {
                "hackathon_id": hackathon_id,
                "name": "Test Hackathon",
                "status": "ACTIVE",
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-12-31T23:59:59",
            },
            "statistics": {
                "participant_count": 50,
                "team_count": 10,
                "submission_count": 8,
                "judge_count": 3,
            },
            "track_distribution": [
                {"track_name": "AI/ML", "team_count": 5},
                {"track_name": "Web3", "team_count": 5},
            ],
            "recent_activity": [
                {
                    "activity_type": "submission",
                    "description": "New submission",
                    "timestamp": "2024-01-01T12:00:00",
                }
            ],
        }

        # Act
        response = organizer_client.get(
            f"/api/v1/dashboard/hackathons/{hackathon_id}"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["hackathon"]["hackathon_id"] == hackathon_id
        assert data["statistics"]["participant_count"] == 50
        assert data["statistics"]["team_count"] == 10
        assert len(data["track_distribution"]) == 2

    @patch("api.routes.dashboard.dashboard_service.get_hackathon_overview")
    def test_get_hackathon_overview_not_found(
        self, mock_get_overview, organizer_client
    ):
        """Should return 404 when hackathon not found"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_get_overview.side_effect = ZeroDBNotFound("Hackathon not found")

        # Act
        response = organizer_client.get(
            f"/api/v1/dashboard/hackathons/{hackathon_id}"
        )

        # Assert
        assert response.status_code == 500

    @patch("api.routes.dashboard.dashboard_service.get_hackathon_overview")
    def test_get_hackathon_overview_unauthorized(
        self, mock_get_overview, builder_client
    ):
        """Should prevent non-organizers from accessing overview"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_get_overview.side_effect = ZeroDBError("Unauthorized")

        # Act
        response = builder_client.get(
            f"/api/v1/dashboard/hackathons/{hackathon_id}"
        )

        # Assert
        assert response.status_code == 500
