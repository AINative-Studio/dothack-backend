"""
Tests for Team Management API Endpoints

Tests all team CRUD endpoints and member management routes.
Uses TestClient for integration testing with mocked dependencies.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.routes.teams import get_current_user, get_zerodb_client, router
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

# Create test app with team router
app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User",
    }


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client"""
    return AsyncMock()


@pytest.fixture
def client(mock_user, mock_zerodb_client):
    """Test client with dependency overrides"""

    async def override_get_current_user():
        return mock_user

    async def override_get_zerodb_client():
        return mock_zerodb_client

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_zerodb_client] = override_get_zerodb_client

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


class TestCreateTeamEndpoint:
    """Test POST /teams - Create team"""

    @patch("api.routes.teams.create_team")
    def test_create_team_success(self, mock_create, client, mock_user):
        """Should create team and return 201"""
        # Arrange
        team_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_create.return_value = {
            "team_id": team_id,
            "hackathon_id": hackathon_id,
            "name": "Test Team",
            "status": "FORMING",
        }

        # Act
        response = client.post(
            "/teams",
            json={
                "hackathon_id": hackathon_id,
                "name": "Test Team",
                "description": "A test team",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == team_id
        assert data["name"] == "Test Team"
        assert data["status"] == "FORMING"

    @patch("api.routes.teams.create_team")
    def test_create_team_minimal_fields(self, mock_create, client):
        """Should create team with only required fields"""
        # Arrange
        team_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_create.return_value = {
            "team_id": team_id,
            "hackathon_id": hackathon_id,
            "name": "Minimal Team",
            "status": "FORMING",
        }

        # Act
        response = client.post(
            "/teams", json={"hackathon_id": hackathon_id, "name": "Minimal Team"}
        )

        # Assert
        assert response.status_code == 201
        assert response.json()["name"] == "Minimal Team"

    @patch("api.routes.teams.create_team")
    def test_create_team_validation_error(self, mock_create, client):
        """Should return 422 for Pydantic validation errors"""
        # Arrange
        # Pydantic validation happens before service call

        # Act
        response = client.post(
            "/teams", json={"hackathon_id": str(uuid.uuid4()), "name": ""}
        )

        # Assert
        assert response.status_code == 422
        # Pydantic returns validation error details
        assert "error" in response.json() or "detail" in response.json()

    def test_create_team_missing_required_fields(self, client):
        """Should return 422 for missing required fields"""
        # Act
        response = client.post("/teams", json={"name": "Test Team"})

        # Assert
        assert response.status_code == 422

    @patch("api.routes.teams.create_team")
    def test_create_team_database_error(self, mock_create, client):
        """Should return 500 for database errors"""
        # Arrange
        mock_create.side_effect = HTTPException(
            status_code=500, detail="Database error"
        )

        # Act
        response = client.post(
            "/teams",
            json={"hackathon_id": str(uuid.uuid4()), "name": "Test Team"},
        )

        # Assert
        assert response.status_code == 500


class TestListTeamsEndpoint:
    """Test GET /teams - List teams"""

    @patch("api.routes.teams.list_teams")
    def test_list_teams_success(self, mock_list, client):
        """Should return list of teams"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_list.return_value = [
            {
                "team_id": str(uuid.uuid4()),
                "hackathon_id": hackathon_id,
                "name": "Team Alpha",
                "status": "ACTIVE",
            },
            {
                "team_id": str(uuid.uuid4()),
                "hackathon_id": hackathon_id,
                "name": "Team Beta",
                "status": "FORMING",
            },
        ]

        # Act
        response = client.get(f"/teams?hackathon_id={hackathon_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 2
        assert data["total"] == 2
        assert data["teams"][0]["name"] == "Team Alpha"

    @patch("api.routes.teams.list_teams")
    def test_list_teams_with_status_filter(self, mock_list, client):
        """Should filter teams by status"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_list.return_value = [
            {
                "team_id": str(uuid.uuid4()),
                "hackathon_id": hackathon_id,
                "name": "Active Team",
                "status": "ACTIVE",
            }
        ]

        # Act
        response = client.get(
            f"/teams?hackathon_id={hackathon_id}&status=ACTIVE"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 1
        assert data["teams"][0]["status"] == "ACTIVE"

    @patch("api.routes.teams.list_teams")
    def test_list_teams_with_pagination(self, mock_list, client):
        """Should support pagination"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_list.return_value = []

        # Act
        response = client.get(
            f"/teams?hackathon_id={hackathon_id}&skip=10&limit=20"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 10
        assert data["limit"] == 20

    @patch("api.routes.teams.list_teams")
    def test_list_teams_empty_result(self, mock_list, client):
        """Should return empty list if no teams"""
        # Arrange
        mock_list.return_value = []

        # Act
        response = client.get(f"/teams?hackathon_id={str(uuid.uuid4())}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["teams"] == []
        assert data["total"] == 0

    def test_list_teams_missing_hackathon_id(self, client):
        """Should return 422 if hackathon_id is missing"""
        # Act
        response = client.get("/teams")

        # Assert
        assert response.status_code == 422


class TestGetTeamEndpoint:
    """Test GET /teams/{team_id} - Get team details"""

    @patch("api.routes.teams.get_team")
    def test_get_team_success(self, mock_get, client):
        """Should return team with members"""
        # Arrange
        team_id = str(uuid.uuid4())
        mock_get.return_value = {
            "team_id": team_id,
            "hackathon_id": str(uuid.uuid4()),
            "name": "Test Team",
            "status": "ACTIVE",
            "members": [
                {
                    "id": str(uuid.uuid4()),
                    "team_id": team_id,
                    "participant_id": str(uuid.uuid4()),
                    "role": "LEAD",
                }
            ],
            "member_count": 1,
        }

        # Act
        response = client.get(f"/teams/{team_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == team_id
        assert len(data["members"]) == 1
        assert data["member_count"] == 1

    @patch("api.routes.teams.get_team")
    def test_get_team_not_found(self, mock_get, client):
        """Should return 404 if team doesn't exist"""
        # Arrange
        mock_get.side_effect = HTTPException(status_code=404, detail="Team not found")

        # Act
        response = client.get(f"/teams/{str(uuid.uuid4())}")

        # Assert
        assert response.status_code == 404

    @patch("api.routes.teams.get_team")
    def test_get_team_timeout_error(self, mock_get, client):
        """Should return 504 on timeout"""
        # Arrange
        mock_get.side_effect = HTTPException(
            status_code=504, detail="Request timed out"
        )

        # Act
        response = client.get(f"/teams/{str(uuid.uuid4())}")

        # Assert
        assert response.status_code == 504


class TestUpdateTeamEndpoint:
    """Test PUT /teams/{team_id} - Update team"""

    @patch("api.routes.teams.update_team")
    def test_update_team_name(self, mock_update, client):
        """Should update team name"""
        # Arrange
        team_id = str(uuid.uuid4())
        mock_update.return_value = {
            "team_id": team_id,
            "hackathon_id": str(uuid.uuid4()),
            "name": "Updated Name",
            "status": "ACTIVE",
        }

        # Act
        response = client.put(f"/teams/{team_id}", json={"name": "Updated Name"})

        # Assert
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    @patch("api.routes.teams.update_team")
    def test_update_team_status(self, mock_update, client):
        """Should update team status"""
        # Arrange
        team_id = str(uuid.uuid4())
        mock_update.return_value = {
            "team_id": team_id,
            "hackathon_id": str(uuid.uuid4()),
            "name": "Test Team",
            "status": "SUBMITTED",
        }

        # Act
        response = client.put(f"/teams/{team_id}", json={"status": "SUBMITTED"})

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "SUBMITTED"

    @patch("api.routes.teams.update_team")
    def test_update_team_multiple_fields(self, mock_update, client):
        """Should update multiple fields"""
        # Arrange
        team_id = str(uuid.uuid4())
        mock_update.return_value = {
            "team_id": team_id,
            "hackathon_id": str(uuid.uuid4()),
            "name": "New Name",
            "description": "New description",
            "status": "ACTIVE",
        }

        # Act
        response = client.put(
            f"/teams/{team_id}",
            json={
                "name": "New Name",
                "description": "New description",
                "status": "ACTIVE",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "New description"

    @patch("api.routes.teams.update_team")
    def test_update_team_not_found(self, mock_update, client):
        """Should return 404 if team doesn't exist"""
        # Arrange
        mock_update.side_effect = HTTPException(
            status_code=404, detail="Team not found"
        )

        # Act
        response = client.put(
            f"/teams/{str(uuid.uuid4())}", json={"name": "New Name"}
        )

        # Assert
        assert response.status_code == 404

    @patch("api.routes.teams.update_team")
    def test_update_team_validation_error(self, mock_update, client):
        """Should return 422 for Pydantic validation errors"""
        # Arrange
        # Pydantic validation happens before service call

        # Act
        response = client.put(
            f"/teams/{str(uuid.uuid4())}", json={"status": "INVALID"}
        )

        # Assert
        assert response.status_code == 422
        # Pydantic returns validation error details


class TestDeleteTeamEndpoint:
    """Test DELETE /teams/{team_id} - Delete team"""

    @patch("api.routes.teams.get_team")
    def test_delete_team_success(self, mock_get, client, mock_zerodb_client):
        """Should delete team and return success"""
        # Arrange
        team_id = str(uuid.uuid4())
        mock_get.return_value = {
            "team_id": team_id,
            "name": "Test Team",
            "members": [
                {"id": str(uuid.uuid4()), "participant_id": str(uuid.uuid4())}
            ],
        }

        mock_zerodb_client.tables.delete_row = AsyncMock()

        # Act
        response = client.delete(f"/teams/{team_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("api.routes.teams.get_team")
    def test_delete_team_not_found(self, mock_get, client):
        """Should return 404 if team doesn't exist"""
        # Arrange
        mock_get.side_effect = HTTPException(status_code=404, detail="Team not found")

        # Act
        response = client.delete(f"/teams/{str(uuid.uuid4())}")

        # Assert
        assert response.status_code == 404

    @patch("api.routes.teams.get_team")
    def test_delete_team_database_error(self, mock_get, client, mock_zerodb_client):
        """Should return 500 on database error"""
        # Arrange
        team_id = str(uuid.uuid4())
        mock_get.return_value = {
            "team_id": team_id,
            "name": "Test Team",
            "members": [],
        }

        mock_zerodb_client.tables.delete_row = AsyncMock(
            side_effect=ZeroDBError("Database error", status_code=500)
        )

        # Act
        response = client.delete(f"/teams/{team_id}")

        # Assert
        assert response.status_code == 500


class TestAddTeamMemberEndpoint:
    """Test POST /teams/{team_id}/members - Add team member"""

    @patch("api.routes.teams.add_team_member")
    def test_add_member_success(self, mock_add, client):
        """Should add member and return 201"""
        # Arrange
        team_id = str(uuid.uuid4())
        participant_id = str(uuid.uuid4())

        mock_add.return_value = {
            "id": str(uuid.uuid4()),
            "team_id": team_id,
            "participant_id": participant_id,
            "role": "MEMBER",
        }

        # Act
        response = client.post(
            f"/teams/{team_id}/members",
            json={"participant_id": participant_id, "role": "MEMBER"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["team_id"] == team_id
        assert data["participant_id"] == participant_id
        assert data["role"] == "MEMBER"

    @patch("api.routes.teams.add_team_member")
    def test_add_member_with_lead_role(self, mock_add, client):
        """Should add member with LEAD role"""
        # Arrange
        team_id = str(uuid.uuid4())
        participant_id = str(uuid.uuid4())

        mock_add.return_value = {
            "id": str(uuid.uuid4()),
            "team_id": team_id,
            "participant_id": participant_id,
            "role": "LEAD",
        }

        # Act
        response = client.post(
            f"/teams/{team_id}/members",
            json={"participant_id": participant_id, "role": "LEAD"},
        )

        # Assert
        assert response.status_code == 201
        assert response.json()["role"] == "LEAD"

    @patch("api.routes.teams.add_team_member")
    def test_add_member_team_not_found(self, mock_add, client):
        """Should return 404 if team doesn't exist"""
        # Arrange
        mock_add.side_effect = HTTPException(status_code=404, detail="Team not found")

        # Act
        response = client.post(
            f"/teams/{str(uuid.uuid4())}/members",
            json={"participant_id": str(uuid.uuid4()), "role": "MEMBER"},
        )

        # Assert
        assert response.status_code == 404

    @patch("api.routes.teams.add_team_member")
    def test_add_member_already_exists(self, mock_add, client):
        """Should return 400 if member already in team"""
        # Arrange
        mock_add.side_effect = HTTPException(
            status_code=400, detail="Participant is already a member of this team"
        )

        # Act
        response = client.post(
            f"/teams/{str(uuid.uuid4())}/members",
            json={"participant_id": str(uuid.uuid4()), "role": "MEMBER"},
        )

        # Assert
        assert response.status_code == 400

    @patch("api.routes.teams.add_team_member")
    def test_add_member_validation_error(self, mock_add, client):
        """Should return 422 for Pydantic validation errors (invalid role)"""
        # Arrange
        # Pydantic validation happens before service call

        # Act
        response = client.post(
            f"/teams/{str(uuid.uuid4())}/members",
            json={"participant_id": str(uuid.uuid4()), "role": "INVALID"},
        )

        # Assert
        assert response.status_code == 422
        # Pydantic returns validation error details


class TestRemoveTeamMemberEndpoint:
    """Test DELETE /teams/{team_id}/members/{participant_id} - Remove member"""

    @patch("api.routes.teams.remove_team_member")
    def test_remove_member_success(self, mock_remove, client):
        """Should remove member and return success"""
        # Arrange
        team_id = str(uuid.uuid4())
        participant_id = str(uuid.uuid4())

        mock_remove.return_value = {"success": True}

        # Act
        response = client.delete(f"/teams/{team_id}/members/{participant_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("api.routes.teams.remove_team_member")
    def test_remove_member_not_found(self, mock_remove, client):
        """Should return 404 if member not in team"""
        # Arrange
        mock_remove.side_effect = HTTPException(
            status_code=404, detail="Member not found in team"
        )

        # Act
        response = client.delete(
            f"/teams/{str(uuid.uuid4())}/members/{str(uuid.uuid4())}"
        )

        # Assert
        assert response.status_code == 404

    @patch("api.routes.teams.remove_team_member")
    def test_remove_member_last_lead(self, mock_remove, client):
        """Should return 400 if attempting to remove last LEAD"""
        # Arrange
        mock_remove.side_effect = HTTPException(
            status_code=400, detail="Cannot remove the last LEAD from the team"
        )

        # Act
        response = client.delete(
            f"/teams/{str(uuid.uuid4())}/members/{str(uuid.uuid4())}"
        )

        # Assert
        assert response.status_code == 400


class TestAuthenticationRequired:
    """Test that all endpoints require authentication"""

    def test_endpoints_require_auth(self):
        """Should return 401 for unauthenticated requests"""
        # Create client without auth override
        test_client = TestClient(app)

        endpoints = [
            ("POST", "/teams", {"hackathon_id": "123", "name": "Test"}),
            ("GET", "/teams?hackathon_id=123", None),
            ("GET", f"/teams/{str(uuid.uuid4())}", None),
            ("PUT", f"/teams/{str(uuid.uuid4())}", {"name": "Test"}),
            ("DELETE", f"/teams/{str(uuid.uuid4())}", None),
            (
                "POST",
                f"/teams/{str(uuid.uuid4())}/members",
                {"participant_id": "123", "role": "MEMBER"},
            ),
            (
                "DELETE",
                f"/teams/{str(uuid.uuid4())}/members/{str(uuid.uuid4())}",
                None,
            ),
        ]

        for method, path, json_data in endpoints:
            if method == "POST":
                response = test_client.post(path, json=json_data)
            elif method == "GET":
                response = test_client.get(path)
            elif method == "PUT":
                response = test_client.put(path, json=json_data)
            elif method == "DELETE":
                response = test_client.delete(path)

            # Should get 401 or 403 (depending on FastAPI security implementation)
            assert response.status_code in [401, 403]


class TestErrorHandling:
    """Test error handling across all endpoints"""

    @patch("api.routes.teams.create_team")
    def test_unexpected_error_handling(self, mock_create, client):
        """Should return 500 for unexpected errors"""
        # Arrange
        mock_create.side_effect = Exception("Unexpected error")

        # Act
        response = client.post(
            "/teams",
            json={"hackathon_id": str(uuid.uuid4()), "name": "Test Team"},
        )

        # Assert
        assert response.status_code == 500

    @patch("api.routes.teams.list_teams")
    def test_timeout_error_propagation(self, mock_list, client):
        """Should propagate timeout errors correctly"""
        # Arrange
        mock_list.side_effect = HTTPException(
            status_code=504, detail="Request timed out"
        )

        # Act
        response = client.get(f"/teams?hackathon_id={str(uuid.uuid4())}")

        # Assert
        assert response.status_code == 504


class TestZeroDBClientDependency:
    """Test ZeroDB client dependency"""

    def test_zerodb_client_initialization_error(self):
        """Should return 503 if ZeroDB client cannot be initialized"""
        # Create app without dependency override
        test_client = TestClient(app)

        # Mock user authentication but fail ZeroDB init
        async def override_get_current_user():
            return {"id": str(uuid.uuid4()), "email": "test@example.com"}

        app.dependency_overrides[get_current_user] = override_get_current_user

        with patch("api.routes.teams.ZeroDBClient") as mock_client_class:
            mock_client_class.side_effect = ValueError("Missing API key")

            # Act
            response = test_client.post(
                "/teams",
                json={"hackathon_id": str(uuid.uuid4()), "name": "Test Team"},
            )

            # Assert
            assert response.status_code == 503

        # Clean up
        app.dependency_overrides.clear()
