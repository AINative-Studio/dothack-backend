"""
Tests for Dashboard API Endpoints

Tests all role-based dashboard endpoints for organizers, builders, and judges.
Uses TestClient for integration testing with mocked dependencies.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from api.routes.dashboard import get_current_user, get_zerodb_client, router
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound


# Create test app with dashboard router
app = FastAPI()
app.include_router(router)


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": str(exc)})


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

    yield TestClient(app, raise_server_exceptions=False)

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

    yield TestClient(app, raise_server_exceptions=False)

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

    yield TestClient(app, raise_server_exceptions=False)

    # Clean up
    app.dependency_overrides.clear()


class TestOrganizerDashboardEndpoint:
    """Test GET /dashboard/organizer - Organizer dashboard"""

    @patch("api.routes.dashboard.dashboard_service.get_organizer_dashboard")
    def test_get_organizer_dashboard_success(
        self, mock_get_dashboard, organizer_client, mock_organizer_user
    ):
        """Should return organizer dashboard with statistics"""
        hackathon_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        mock_get_dashboard.return_value = {
            "my_hackathons": [
                {
                    "hackathon_id": hackathon_id,
                    "name": "Test Hackathon",
                    "status": "ACTIVE",
                    "start_date": now,
                    "end_date": now,
                    "participant_count": 50,
                    "team_count": 10,
                    "submission_count": 8,
                }
            ],
            "total_participants": 50,
            "total_teams": 10,
            "total_submissions": 8,
            "pending_judgments": 8,
        }

        response = organizer_client.get("/api/v1/dashboard/organizer")

        assert response.status_code == 200
        data = response.json()
        assert data["total_participants"] == 50
        assert data["total_teams"] == 10
        assert data["total_submissions"] == 8
        assert data["pending_judgments"] == 8
        assert len(data["my_hackathons"]) == 1

    @patch("api.routes.dashboard.dashboard_service.get_organizer_dashboard")
    def test_get_organizer_dashboard_empty(
        self, mock_get_dashboard, organizer_client
    ):
        """Should return empty dashboard when no hackathons organized"""
        mock_get_dashboard.return_value = {
            "my_hackathons": [],
            "total_participants": 0,
            "total_teams": 0,
            "total_submissions": 0,
            "pending_judgments": 0,
        }

        response = organizer_client.get("/api/v1/dashboard/organizer")

        assert response.status_code == 200
        data = response.json()
        assert data["total_participants"] == 0
        assert len(data["my_hackathons"]) == 0


class TestBuilderDashboardEndpoint:
    """Test GET /dashboard/builder - Builder dashboard"""

    @patch("api.routes.dashboard.dashboard_service.get_builder_dashboard")
    def test_get_builder_dashboard_success(
        self, mock_get_dashboard, builder_client, mock_builder_user
    ):
        """Should return builder dashboard with participation info"""
        hackathon_id = str(uuid.uuid4())
        team_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        future = (datetime.utcnow() + timedelta(days=30)).isoformat()

        mock_get_dashboard.return_value = {
            "registered_hackathons": [
                {
                    "hackathon_id": hackathon_id,
                    "name": "Test Hackathon",
                    "status": "ACTIVE",
                    "start_date": now,
                    "end_date": future,
                    "location": "San Francisco",
                    "my_role": "builder",
                }
            ],
            "my_teams": [
                {
                    "team_id": team_id,
                    "name": "My Team",
                    "hackathon_id": hackathon_id,
                    "hackathon_name": "Test Hackathon",
                    "status": "ACTIVE",
                    "member_count": 3,
                    "my_role": "MEMBER",
                }
            ],
            "my_submissions": [
                {
                    "submission_id": str(uuid.uuid4()),
                    "project_id": str(uuid.uuid4()),
                    "project_name": "My Project",
                    "team_id": team_id,
                    "team_name": "My Team",
                    "hackathon_id": hackathon_id,
                    "hackathon_name": "Test Hackathon",
                    "submitted_at": now,
                    "status": "SUBMITTED",
                }
            ],
            "upcoming_deadlines": [
                {
                    "hackathon_id": hackathon_id,
                    "hackathon_name": "Test Hackathon",
                    "deadline_type": "submission",
                    "deadline": future,
                    "days_remaining": 30,
                }
            ],
        }

        response = builder_client.get("/api/v1/dashboard/builder")

        assert response.status_code == 200
        data = response.json()
        assert len(data["registered_hackathons"]) == 1
        assert len(data["my_teams"]) == 1
        assert len(data["my_submissions"]) == 1
        assert len(data["upcoming_deadlines"]) == 1

    @patch("api.routes.dashboard.dashboard_service.get_builder_dashboard")
    def test_get_builder_dashboard_empty(self, mock_get_dashboard, builder_client):
        """Should return empty dashboard when no participation"""
        mock_get_dashboard.return_value = {
            "registered_hackathons": [],
            "my_teams": [],
            "my_submissions": [],
            "upcoming_deadlines": [],
        }

        response = builder_client.get("/api/v1/dashboard/builder")

        assert response.status_code == 200
        data = response.json()
        assert len(data["registered_hackathons"]) == 0
        assert len(data["my_teams"]) == 0


class TestJudgeDashboardEndpoint:
    """Test GET /dashboard/judge - Judge dashboard"""

    @patch("api.routes.dashboard.dashboard_service.get_judge_dashboard")
    def test_get_judge_dashboard_success(
        self, mock_get_dashboard, judge_client, mock_judge_user
    ):
        """Should return judge dashboard with judging assignments"""
        hackathon_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        future = (datetime.utcnow() + timedelta(days=30)).isoformat()

        mock_get_dashboard.return_value = {
            "assigned_hackathons": [
                {
                    "hackathon_id": hackathon_id,
                    "name": "Test Hackathon",
                    "status": "ACTIVE",
                    "start_date": now,
                    "end_date": future,
                    "assigned_submissions": 8,
                    "completed_judgments": 5,
                }
            ],
            "submissions_to_judge": 3,
            "completed_judgments": 5,
            "pending_submissions": [],
        }

        response = judge_client.get("/api/v1/dashboard/judge")

        assert response.status_code == 200
        data = response.json()
        assert len(data["assigned_hackathons"]) == 1
        assert data["submissions_to_judge"] == 3
        assert data["completed_judgments"] == 5

    @patch("api.routes.dashboard.dashboard_service.get_judge_dashboard")
    def test_get_judge_dashboard_empty(self, mock_get_dashboard, judge_client):
        """Should return empty dashboard when no assignments"""
        mock_get_dashboard.return_value = {
            "assigned_hackathons": [],
            "submissions_to_judge": 0,
            "completed_judgments": 0,
            "pending_submissions": [],
        }

        response = judge_client.get("/api/v1/dashboard/judge")

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
        hackathon_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        future = (datetime.utcnow() + timedelta(days=30)).isoformat()

        mock_get_overview.return_value = {
            "hackathon_id": hackathon_id,
            "name": "Test Hackathon",
            "status": "ACTIVE",
            "start_date": now,
            "end_date": future,
            "location": "San Francisco",
            "stats": {
                "participant_count": 50,
                "team_count": 10,
                "submission_count": 8,
                "builder_count": 40,
                "judge_count": 3,
                "track_distribution": {"AI/ML": 5, "Web3": 5},
            },
            "recent_activity": [
                {
                    "activity_type": "submission",
                    "description": "New submission",
                    "timestamp": now,
                }
            ],
        }

        response = organizer_client.get(
            f"/api/v1/dashboard/hackathons/{hackathon_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["hackathon_id"] == hackathon_id
        assert data["stats"]["participant_count"] == 50
        assert data["stats"]["team_count"] == 10

    @patch("api.routes.dashboard.dashboard_service.get_hackathon_overview")
    def test_get_hackathon_overview_not_found(
        self, mock_get_overview, organizer_client
    ):
        """Should return 500 when hackathon not found (ZeroDBNotFound propagates)"""
        hackathon_id = str(uuid.uuid4())
        mock_get_overview.side_effect = ZeroDBNotFound("Hackathon not found")

        response = organizer_client.get(
            f"/api/v1/dashboard/hackathons/{hackathon_id}"
        )

        assert response.status_code == 500

    @patch("api.routes.dashboard.dashboard_service.get_hackathon_overview")
    def test_get_hackathon_overview_unauthorized(
        self, mock_get_overview, builder_client
    ):
        """Should prevent non-organizers from accessing overview"""
        hackathon_id = str(uuid.uuid4())
        mock_get_overview.side_effect = ZeroDBError("Unauthorized")

        response = builder_client.get(
            f"/api/v1/dashboard/hackathons/{hackathon_id}"
        )

        assert response.status_code == 500
