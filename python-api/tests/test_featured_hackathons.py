"""
Tests for Featured Hackathons API Endpoints

Tests all featured hackathon management endpoints including public read access.
Uses TestClient for integration testing with mocked dependencies.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from api.routes.featured_hackathons import (
    get_current_user,
    get_zerodb_client,
    require_admin,
    router,
)
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound


# Create test app with featured_hackathons router
app = FastAPI()
app.include_router(router)


@pytest.fixture
def mock_admin_user():
    """Mock admin user"""
    return {
        "id": str(uuid.uuid4()),
        "email": "admin@example.com",
        "name": "Admin User",
        "role": "ADMIN",
    }


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client"""
    return AsyncMock()


@pytest.fixture
def client(mock_admin_user, mock_zerodb_client):
    """Test client with dependency overrides"""

    async def override_get_current_user():
        return mock_admin_user

    async def override_get_zerodb_client():
        return mock_zerodb_client

    async def override_require_admin():
        return None

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_zerodb_client] = override_get_zerodb_client
    app.dependency_overrides[require_admin] = override_require_admin

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def public_client(mock_zerodb_client):
    """Public test client without authentication"""

    async def override_get_zerodb_client():
        return mock_zerodb_client

    app.dependency_overrides[get_zerodb_client] = override_get_zerodb_client

    yield TestClient(app)

    # Clean up
    app.dependency_overrides.clear()


class TestListFeaturedHackathonsEndpoint:
    """Test GET /featured-hackathons - List featured hackathons (PUBLIC)"""

    @patch("api.routes.featured_hackathons.featured_hackathon_service.list_featured")
    def test_list_featured_hackathons_success(self, mock_list, public_client):
        """Should return list of featured hackathons (public access)"""
        # Arrange
        featured1_id = str(uuid.uuid4())
        featured2_id = str(uuid.uuid4())
        hackathon1_id = str(uuid.uuid4())
        hackathon2_id = str(uuid.uuid4())

        mock_list.return_value = {
            "featured_hackathons": [
                {
                    "featured_id": featured1_id,
                    "hackathon_id": hackathon1_id,
                    "display_order": 1,
                    "featured_until": "2024-12-31T23:59:59",
                    "created_at": "2024-01-01T00:00:00",
                },
                {
                    "featured_id": featured2_id,
                    "hackathon_id": hackathon2_id,
                    "display_order": 2,
                    "featured_until": None,
                    "created_at": "2024-01-02T00:00:00",
                },
            ],
            "total": 2,
        }

        # Act
        response = public_client.get("/api/v1/featured-hackathons")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["featured_hackathons"]) == 2
        assert data["featured_hackathons"][0]["display_order"] == 1

    @patch("api.routes.featured_hackathons.featured_hackathon_service.list_featured")
    def test_list_featured_hackathons_empty(self, mock_list, public_client):
        """Should return empty list when no featured hackathons"""
        # Arrange
        mock_list.return_value = {"featured_hackathons": [], "total": 0}

        # Act
        response = public_client.get("/api/v1/featured-hackathons")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["featured_hackathons"]) == 0


class TestGetFeaturedHackathonEndpoint:
    """Test GET /featured-hackathons/{featured_id} - Get featured hackathon (PUBLIC)"""

    @patch("api.routes.featured_hackathons.featured_hackathon_service.get_featured")
    def test_get_featured_hackathon_success(self, mock_get, public_client):
        """Should return single featured hackathon (public access)"""
        # Arrange
        featured_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_get.return_value = {
            "featured_id": featured_id,
            "hackathon_id": hackathon_id,
            "display_order": 1,
            "featured_until": "2024-12-31T23:59:59",
            "created_at": "2024-01-01T00:00:00",
        }

        # Act
        response = public_client.get(f"/api/v1/featured-hackathons/{featured_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["featured_id"] == featured_id
        assert data["hackathon_id"] == hackathon_id

    @patch("api.routes.featured_hackathons.featured_hackathon_service.get_featured")
    def test_get_featured_hackathon_not_found(self, mock_get, public_client):
        """Should return 404 when featured hackathon not found"""
        # Arrange
        featured_id = str(uuid.uuid4())
        mock_get.side_effect = ZeroDBNotFound("Featured hackathon not found")

        # Act
        response = public_client.get(f"/api/v1/featured-hackathons/{featured_id}")

        # Assert
        assert response.status_code == 500


class TestCreateFeaturedHackathonEndpoint:
    """Test POST /featured-hackathons - Create featured hackathon (ADMIN)"""

    @patch("api.routes.featured_hackathons.featured_hackathon_service.create_featured")
    def test_create_featured_hackathon_success(
        self, mock_create, client, mock_admin_user
    ):
        """Should create featured hackathon and return 201"""
        # Arrange
        featured_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_create.return_value = {
            "featured_id": featured_id,
            "hackathon_id": hackathon_id,
            "display_order": 1,
            "featured_until": "2024-12-31T23:59:59",
            "created_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            "/api/v1/featured-hackathons",
            json={
                "hackathon_id": hackathon_id,
                "display_order": 1,
                "featured_until": "2024-12-31T23:59:59",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["featured_id"] == featured_id
        assert data["hackathon_id"] == hackathon_id
        assert data["display_order"] == 1

    @patch("api.routes.featured_hackathons.featured_hackathon_service.create_featured")
    def test_create_featured_hackathon_no_expiration(self, mock_create, client):
        """Should create featured hackathon without expiration date"""
        # Arrange
        featured_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_create.return_value = {
            "featured_id": featured_id,
            "hackathon_id": hackathon_id,
            "display_order": 1,
            "featured_until": None,
            "created_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.post(
            "/api/v1/featured-hackathons",
            json={"hackathon_id": hackathon_id, "display_order": 1},
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["featured_until"] is None

    @patch("api.routes.featured_hackathons.featured_hackathon_service.create_featured")
    def test_create_featured_hackathon_duplicate(self, mock_create, client):
        """Should reject duplicate featured hackathon"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        mock_create.side_effect = ZeroDBError("Hackathon already featured")

        # Act
        response = client.post(
            "/api/v1/featured-hackathons",
            json={"hackathon_id": hackathon_id, "display_order": 1},
        )

        # Assert
        assert response.status_code == 500


class TestUpdateFeaturedHackathonEndpoint:
    """Test PUT /featured-hackathons/{featured_id} - Update featured hackathon (ADMIN)"""

    @patch("api.routes.featured_hackathons.featured_hackathon_service.update_featured")
    def test_update_featured_hackathon_success(
        self, mock_update, client, mock_admin_user
    ):
        """Should update featured hackathon and return updated data"""
        # Arrange
        featured_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_update.return_value = {
            "featured_id": featured_id,
            "hackathon_id": hackathon_id,
            "display_order": 2,
            "featured_until": "2024-12-31T23:59:59",
            "created_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.put(
            f"/api/v1/featured-hackathons/{featured_id}",
            json={"display_order": 2, "featured_until": "2024-12-31T23:59:59"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["display_order"] == 2

    @patch("api.routes.featured_hackathons.featured_hackathon_service.get_featured")
    def test_update_featured_hackathon_no_changes(self, mock_get, client):
        """Should return existing featured hackathon when no update data"""
        # Arrange
        featured_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_get.return_value = {
            "featured_id": featured_id,
            "hackathon_id": hackathon_id,
            "display_order": 1,
            "featured_until": None,
            "created_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.put(
            f"/api/v1/featured-hackathons/{featured_id}",
            json={},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["display_order"] == 1


class TestUpdateDisplayOrderEndpoint:
    """Test PATCH /featured-hackathons/{featured_id}/order - Update display order (ADMIN)"""

    @patch("api.routes.featured_hackathons.featured_hackathon_service.update_featured")
    def test_update_display_order_success(self, mock_update, client, mock_admin_user):
        """Should update display order"""
        # Arrange
        featured_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        mock_update.return_value = {
            "featured_id": featured_id,
            "hackathon_id": hackathon_id,
            "display_order": 5,
            "featured_until": None,
            "created_at": "2024-01-01T00:00:00",
        }

        # Act
        response = client.patch(
            f"/api/v1/featured-hackathons/{featured_id}/order",
            params={"display_order": 5},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["display_order"] == 5


class TestDeleteFeaturedHackathonEndpoint:
    """Test DELETE /featured-hackathons/{featured_id} - Remove from featured (ADMIN)"""

    @patch("api.routes.featured_hackathons.featured_hackathon_service.delete_featured")
    def test_delete_featured_hackathon_success(
        self, mock_delete, client, mock_admin_user
    ):
        """Should delete featured hackathon and return 204"""
        # Arrange
        featured_id = str(uuid.uuid4())
        mock_delete.return_value = None

        # Act
        response = client.delete(f"/api/v1/featured-hackathons/{featured_id}")

        # Assert
        assert response.status_code == 204

    @patch("api.routes.featured_hackathons.featured_hackathon_service.delete_featured")
    def test_delete_featured_hackathon_not_found(self, mock_delete, client):
        """Should return 404 when featured hackathon not found"""
        # Arrange
        featured_id = str(uuid.uuid4())
        mock_delete.side_effect = ZeroDBNotFound("Featured hackathon not found")

        # Act
        response = client.delete(f"/api/v1/featured-hackathons/{featured_id}")

        # Assert
        assert response.status_code == 500
