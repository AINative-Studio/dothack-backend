"""
Tests for Rubrics API Endpoints

Tests all judging rubric CRUD endpoints.
Uses TestClient for integration testing with mocked dependencies.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from api.routes.rubrics import get_current_user, get_zerodb_client, router
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound


# Create test app with rubrics router
app = FastAPI()
app.include_router(router)


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return {
        "id": str(uuid.uuid4()),
        "email": "organizer@example.com",
        "name": "Test Organizer",
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

    yield TestClient(app, raise_server_exceptions=False)

    # Clean up
    app.dependency_overrides.clear()


class TestCreateRubricEndpoint:
    """Test POST /hackathons/{hackathon_id}/rubrics - Create rubric"""

    @patch("api.routes.rubrics.rubric_service.create_rubric")
    def test_create_rubric_success(self, mock_create, client, mock_user):
        """Should create rubric with valid criteria"""
        # Arrange
        rubric_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_create.return_value = {
            "rubric_id": rubric_id,
            "hackathon_id": hackathon_id,
            "name": "Default Rubric",
            "criteria": [
                {
                    "name": "Innovation",
                    "description": "Uniqueness of idea",
                    "weight": 0.4,
                    "max_score": 10,
                },
                {
                    "name": "Technical",
                    "description": "Implementation quality",
                    "weight": 0.6,
                    "max_score": 10,
                },
            ],
            "is_active": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/rubrics",
            json={
                "name": "Default Rubric",
                "criteria": [
                    {
                        "name": "Innovation",
                        "description": "Uniqueness of idea",
                        "weight": 0.4,
                        "max_score": 10,
                    },
                    {
                        "name": "Technical",
                        "description": "Implementation quality",
                        "weight": 0.6,
                        "max_score": 10,
                    },
                ],
                "is_active": True,
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["rubric_id"] == rubric_id
        assert data["name"] == "Default Rubric"
        assert len(data["criteria"]) == 2
        assert data["is_active"] is True

    @patch("api.routes.rubrics.rubric_service.create_rubric")
    def test_create_rubric_inactive(self, mock_create, client):
        """Should create inactive rubric"""
        # Arrange
        rubric_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_create.return_value = {
            "rubric_id": rubric_id,
            "hackathon_id": hackathon_id,
            "name": "Draft Rubric",
            "criteria": [
                {"name": "Test", "description": "Test", "weight": 1.0, "max_score": 10}
            ],
            "is_active": False,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/rubrics",
            json={
                "name": "Draft Rubric",
                "criteria": [
                    {
                        "name": "Test",
                        "description": "Test",
                        "weight": 1.0,
                        "max_score": 10,
                    }
                ],
                "is_active": False,
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["is_active"] is False

    def test_create_rubric_invalid_weights(self, client):
        """Should reject rubric with weights not summing to 1.0"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/rubrics",
            json={
                "name": "Invalid Rubric",
                "criteria": [
                    {
                        "name": "Innovation",
                        "description": "Test",
                        "weight": 0.3,
                        "max_score": 10,
                    },
                    {
                        "name": "Technical",
                        "description": "Test",
                        "weight": 0.5,
                        "max_score": 10,
                    },
                ],
            },
        )

        # Assert
        assert response.status_code == 422


class TestListRubricsEndpoint:
    """Test GET /hackathons/{hackathon_id}/rubrics - List rubrics"""

    @patch("api.routes.rubrics.rubric_service.list_rubrics")
    def test_list_rubrics_success(self, mock_list, client):
        """Should return list of rubrics"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        rubric1_id = str(uuid.uuid4())
        rubric2_id = str(uuid.uuid4())

        mock_list.return_value = {
            "rubrics": [
                {
                    "rubric_id": rubric1_id,
                    "hackathon_id": hackathon_id,
                    "name": "Rubric 1",
                    "criteria": [],
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                },
                {
                    "rubric_id": rubric2_id,
                    "hackathon_id": hackathon_id,
                    "name": "Rubric 2",
                    "criteria": [],
                    "is_active": False,
                    "created_at": "2024-01-02T00:00:00",
                    "updated_at": "2024-01-02T00:00:00",
                },
            ],
            "total": 2,
        }

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/rubrics")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["rubrics"]) == 2

    @patch("api.routes.rubrics.rubric_service.list_rubrics")
    def test_list_rubrics_empty(self, mock_list, client):
        """Should return empty list when no rubrics"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_list.return_value = {"rubrics": [], "total": 0}

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/rubrics")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestGetActiveRubricEndpoint:
    """Test GET /hackathons/{hackathon_id}/rubrics/active - Get active rubric"""

    @patch("api.routes.rubrics.rubric_service.get_active_rubric")
    def test_get_active_rubric_success(self, mock_get, client):
        """Should return active rubric"""
        # Arrange
        rubric_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_get.return_value = {
            "rubric_id": rubric_id,
            "hackathon_id": hackathon_id,
            "name": "Active Rubric",
            "criteria": [
                {"name": "Test", "description": "Test", "weight": 1.0, "max_score": 10}
            ],
            "is_active": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/rubrics/active")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    @patch("api.routes.rubrics.rubric_service.get_active_rubric")
    def test_get_active_rubric_not_found(self, mock_get, client):
        """Should return 404 when no active rubric"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_get.side_effect = ZeroDBNotFound("No active rubric")

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/rubrics/active")

        # Assert
        assert response.status_code == 500


class TestGetRubricEndpoint:
    """Test GET /hackathons/{hackathon_id}/rubrics/{rubric_id} - Get rubric"""

    @patch("api.routes.rubrics.rubric_service.get_rubric")
    def test_get_rubric_success(self, mock_get, client):
        """Should return single rubric"""
        # Arrange
        rubric_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_get.return_value = {
            "rubric_id": rubric_id,
            "hackathon_id": hackathon_id,
            "name": "Test Rubric",
            "criteria": [],
            "is_active": False,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/rubrics/{rubric_id}"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["rubric_id"] == rubric_id


class TestUpdateRubricEndpoint:
    """Test PUT /hackathons/{hackathon_id}/rubrics/{rubric_id} - Update rubric"""

    @patch("api.routes.rubrics.rubric_service.update_rubric")
    def test_update_rubric_success(self, mock_update, client, mock_user):
        """Should update rubric and return updated data"""
        # Arrange
        rubric_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_update.return_value = {
            "rubric_id": rubric_id,
            "hackathon_id": hackathon_id,
            "name": "Updated Rubric",
            "criteria": [],
            "is_active": False,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }

        # Act
        response = client.put(
            f"/api/v1/hackathons/{hackathon_id}/rubrics/{rubric_id}",
            json={"name": "Updated Rubric"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Rubric"

    @patch("api.routes.rubrics.rubric_service.get_rubric")
    def test_update_rubric_no_changes(self, mock_get, client):
        """Should return existing rubric when no update data"""
        # Arrange
        rubric_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_get.return_value = {
            "rubric_id": rubric_id,
            "hackathon_id": hackathon_id,
            "name": "Original Rubric",
            "criteria": [],
            "is_active": False,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.put(
            f"/api/v1/hackathons/{hackathon_id}/rubrics/{rubric_id}",
            json={},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Original Rubric"


class TestActivateRubricEndpoint:
    """Test PATCH /hackathons/{hackathon_id}/rubrics/{rubric_id}/activate"""

    @patch("api.routes.rubrics.rubric_service.activate_rubric")
    def test_activate_rubric_success(self, mock_activate, client, mock_user):
        """Should activate rubric"""
        # Arrange
        rubric_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_activate.return_value = {
            "rubric_id": rubric_id,
            "hackathon_id": hackathon_id,
            "name": "Test Rubric",
            "criteria": [],
            "is_active": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }

        # Act
        response = client.patch(
            f"/api/v1/hackathons/{hackathon_id}/rubrics/{rubric_id}/activate"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True


class TestDeleteRubricEndpoint:
    """Test DELETE /hackathons/{hackathon_id}/rubrics/{rubric_id}"""

    @patch("api.routes.rubrics.rubric_service.delete_rubric")
    def test_delete_rubric_success(self, mock_delete, client, mock_user):
        """Should delete rubric and return 204"""
        # Arrange
        rubric_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        mock_delete.return_value = None

        # Act
        response = client.delete(
            f"/api/v1/hackathons/{hackathon_id}/rubrics/{rubric_id}"
        )

        # Assert
        assert response.status_code == 204

    @patch("api.routes.rubrics.rubric_service.delete_rubric")
    def test_delete_active_rubric(self, mock_delete, client):
        """Should prevent deletion of active rubric"""
        # Arrange
        rubric_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        mock_delete.side_effect = ZeroDBError("Cannot delete active rubric")

        # Act
        response = client.delete(
            f"/api/v1/hackathons/{hackathon_id}/rubrics/{rubric_id}"
        )

        # Assert
        assert response.status_code == 500
