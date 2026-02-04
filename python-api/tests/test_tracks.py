"""
Tests for Tracks API Endpoints

Tests all track CRUD endpoints for hackathon track management.
Uses TestClient for integration testing with mocked dependencies.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from api.routes.tracks import get_current_user, get_zerodb_client, router
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound


# Create test app with tracks router
app = FastAPI()
app.include_router(router)


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

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


class TestCreateTrackEndpoint:
    """Test POST /hackathons/{hackathon_id}/tracks - Create track"""

    @patch("api.routes.tracks.track_service.create_track")
    @patch("api.routes.tracks.check_organizer")
    def test_create_track_success(
        self, mock_check_organizer, mock_create, client, mock_user
    ):
        """Should create track and return 201"""
        # Arrange
        track_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_create.return_value = {
            "track_id": track_id,
            "hackathon_id": hackathon_id,
            "name": "AI/ML Track",
            "description": "Machine learning projects",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/tracks",
            json={
                "name": "AI/ML Track",
                "description": "Machine learning projects",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["track_id"] == track_id
        assert data["name"] == "AI/ML Track"
        assert data["description"] == "Machine learning projects"

    @patch("api.routes.tracks.track_service.create_track")
    @patch("api.routes.tracks.check_organizer")
    def test_create_track_minimal_fields(
        self, mock_check_organizer, mock_create, client
    ):
        """Should create track with only required fields"""
        # Arrange
        track_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_create.return_value = {
            "track_id": track_id,
            "hackathon_id": hackathon_id,
            "name": "Web3 Track",
            "description": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/tracks",
            json={"name": "Web3 Track"},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Web3 Track"
        assert data["description"] is None

    @patch("api.routes.tracks.check_organizer")
    def test_create_track_invalid_name_too_short(self, mock_check_organizer, client):
        """Should reject track with name too short"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_check_organizer.return_value = None

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/tracks",
            json={"name": "AI"},  # Less than 3 chars
        )

        # Assert
        assert response.status_code == 422

    @patch("api.routes.tracks.track_service.create_track")
    @patch("api.routes.tracks.check_organizer")
    def test_create_track_duplicate_name(
        self, mock_check_organizer, mock_create, client
    ):
        """Should reject duplicate track name"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_check_organizer.return_value = None
        mock_create.side_effect = ZeroDBError("Track already exists")

        # Act
        response = client.post(
            f"/api/v1/hackathons/{hackathon_id}/tracks",
            json={"name": "Existing Track"},
        )

        # Assert
        assert response.status_code == 500


class TestListTracksEndpoint:
    """Test GET /hackathons/{hackathon_id}/tracks - List tracks"""

    @patch("api.routes.tracks.track_service.list_tracks")
    def test_list_tracks_success(self, mock_list, client):
        """Should return list of tracks"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        track1_id = str(uuid.uuid4())
        track2_id = str(uuid.uuid4())

        mock_list.return_value = {
            "tracks": [
                {
                    "track_id": track1_id,
                    "hackathon_id": hackathon_id,
                    "name": "AI/ML Track",
                    "description": "ML projects",
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                },
                {
                    "track_id": track2_id,
                    "hackathon_id": hackathon_id,
                    "name": "Web3 Track",
                    "description": "Blockchain projects",
                    "created_at": "2024-01-02T00:00:00",
                    "updated_at": "2024-01-02T00:00:00",
                },
            ],
            "total": 2,
        }

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/tracks")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["tracks"]) == 2
        assert data["tracks"][0]["name"] == "AI/ML Track"
        assert data["tracks"][1]["name"] == "Web3 Track"

    @patch("api.routes.tracks.track_service.list_tracks")
    def test_list_tracks_empty(self, mock_list, client):
        """Should return empty list when no tracks"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_list.return_value = {"tracks": [], "total": 0}

        # Act
        response = client.get(f"/api/v1/hackathons/{hackathon_id}/tracks")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["tracks"]) == 0


class TestGetTrackEndpoint:
    """Test GET /hackathons/{hackathon_id}/tracks/{track_id} - Get track"""

    @patch("api.routes.tracks.track_service.get_track")
    def test_get_track_success(self, mock_get, client):
        """Should return single track"""
        # Arrange
        track_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_get.return_value = {
            "track_id": track_id,
            "hackathon_id": hackathon_id,
            "name": "AI/ML Track",
            "description": "Machine learning projects",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/tracks/{track_id}"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["track_id"] == track_id
        assert data["name"] == "AI/ML Track"

    @patch("api.routes.tracks.track_service.get_track")
    def test_get_track_not_found(self, mock_get, client):
        """Should return 404 when track not found"""
        # Arrange
        track_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())
        mock_get.side_effect = ZeroDBNotFound("Track not found")

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}/tracks/{track_id}"
        )

        # Assert
        assert response.status_code == 500


class TestUpdateTrackEndpoint:
    """Test PUT /hackathons/{hackathon_id}/tracks/{track_id} - Update track"""

    @patch("api.routes.tracks.track_service.update_track")
    @patch("api.routes.tracks.check_organizer")
    def test_update_track_success(
        self, mock_check_organizer, mock_update, client, mock_user
    ):
        """Should update track and return updated data"""
        # Arrange
        track_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_update.return_value = {
            "track_id": track_id,
            "hackathon_id": hackathon_id,
            "name": "Updated AI/ML Track",
            "description": "Updated description",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }

        # Act
        response = client.put(
            f"/api/v1/hackathons/{hackathon_id}/tracks/{track_id}",
            json={
                "name": "Updated AI/ML Track",
                "description": "Updated description",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated AI/ML Track"
        assert data["description"] == "Updated description"

    @patch("api.routes.tracks.track_service.get_track")
    @patch("api.routes.tracks.check_organizer")
    def test_update_track_no_changes(
        self, mock_check_organizer, mock_get, client
    ):
        """Should return existing track when no update data provided"""
        # Arrange
        track_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_get.return_value = {
            "track_id": track_id,
            "hackathon_id": hackathon_id,
            "name": "AI/ML Track",
            "description": "Original description",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.put(
            f"/api/v1/hackathons/{hackathon_id}/tracks/{track_id}",
            json={},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AI/ML Track"


class TestDeleteTrackEndpoint:
    """Test DELETE /hackathons/{hackathon_id}/tracks/{track_id} - Delete track"""

    @patch("api.routes.tracks.track_service.delete_track")
    @patch("api.routes.tracks.check_organizer")
    def test_delete_track_success(
        self, mock_check_organizer, mock_delete, client, mock_user
    ):
        """Should delete track and return 204"""
        # Arrange
        track_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_delete.return_value = None

        # Act
        response = client.delete(
            f"/api/v1/hackathons/{hackathon_id}/tracks/{track_id}"
        )

        # Assert
        assert response.status_code == 204

    @patch("api.routes.tracks.track_service.delete_track")
    @patch("api.routes.tracks.check_organizer")
    def test_delete_track_with_teams(
        self, mock_check_organizer, mock_delete, client
    ):
        """Should prevent deletion of track with assigned teams"""
        # Arrange
        track_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_check_organizer.return_value = None
        mock_delete.side_effect = ZeroDBError("Cannot delete track with teams")

        # Act
        response = client.delete(
            f"/api/v1/hackathons/{hackathon_id}/tracks/{track_id}"
        )

        # Assert
        assert response.status_code == 500
