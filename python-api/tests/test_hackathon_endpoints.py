"""
Tests for Hackathon API Endpoints

Comprehensive test suite for hackathon CRUD endpoints with authentication,
authorization, validation, and error handling.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from api.dependencies import get_current_user
from api.routes.hackathons import router
from fastapi import status
from fastapi.testclient import TestClient
from main import app


# Default fields required by HackathonResponse schema
HACKATHON_RESPONSE_DEFAULTS = {
    "registration_deadline": None,
    "max_participants": None,
    "website_url": None,
    "logo_url": None,
    "is_online": False,
    "participant_count": 0,
    "prizes": None,
    "rules": None,
}


def _hackathon_response(**overrides):
    """Build a complete hackathon response dict with required defaults."""
    data = {**HACKATHON_RESPONSE_DEFAULTS}
    data.update(overrides)
    return data


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    return {"id": str(uuid.uuid4()), "email": "test@example.com", "name": "Test User", "role": "ADMIN", "email_verified": True}


@pytest.fixture
def auth_client(mock_auth_user):
    """Test client with auth and zerodb dependencies overridden."""
    from api.routes.hackathons import get_zerodb_client
    from unittest.mock import MagicMock

    async def override_auth():
        return mock_auth_user

    def override_zerodb():
        return MagicMock()

    app.dependency_overrides[get_current_user] = override_auth
    app.dependency_overrides[get_zerodb_client] = override_zerodb
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_zerodb_client, None)


@pytest.fixture
def unauth_client():
    """Test client WITHOUT auth override (for testing 401s)."""
    # Clear any overrides to ensure real auth is used
    app.dependency_overrides.pop(get_current_user, None)
    return TestClient(app)


class TestCreateHackathon:
    """Test POST /api/v1/hackathons endpoint"""

    def setup_method(self):
        """Setup test fixtures"""
        self.valid_payload = {
            "name": "AI Hackathon 2025",
            "description": "Build innovative AI applications",
            "organizer_id": str(uuid.uuid4()),
            "start_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=32)).isoformat(),
            "location": "San Francisco, CA",
            "status": "draft",
        }

    @patch("services.hackathon_service.create_hackathon")
    def test_create_hackathon_success(self, mock_create, auth_client, mock_auth_user):
        """Should successfully create hackathon"""
        # Arrange
        user_id = mock_auth_user["id"]
        self.valid_payload["organizer_id"] = user_id

        hackathon_id = str(uuid.uuid4())
        mock_create.return_value = {
            "hackathon_id": hackathon_id,
            **self.valid_payload,
            **HACKATHON_RESPONSE_DEFAULTS,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Act
        response = auth_client.post(
            "/api/v1/hackathons",
            json=self.valid_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["hackathon_id"] == hackathon_id
        assert data["name"] == self.valid_payload["name"]
        assert data["status"] == "draft"
        mock_create.assert_called_once()

    def test_create_hackathon_unauthorized(self, unauth_client):
        """Should return 401 without authentication"""
        # Act
        response = unauth_client.post("/api/v1/hackathons", json=self.valid_payload)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_hackathon_forbidden_organizer_mismatch(self, auth_client, mock_auth_user):
        """Should return 403 if organizer_id doesn't match authenticated user"""
        # Arrange
        different_user_id = str(uuid.uuid4())
        self.valid_payload["organizer_id"] = different_user_id

        # Act
        response = auth_client.post(
            "/api/v1/hackathons",
            json=self.valid_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        error_msg = data.get("detail", "") or data.get("error", {}).get("message", "")
        assert "organizer_id must match" in error_msg

    def test_create_hackathon_validation_error_end_before_start(self, auth_client, mock_auth_user):
        """Should return 400 if end_date is before start_date"""
        # Arrange
        invalid_payload = {
            **self.valid_payload,
            "organizer_id": mock_auth_user["id"],
            "start_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=25)).isoformat(),  # Before start
        }

        # Act
        response = auth_client.post(
            "/api/v1/hackathons",
            json=invalid_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_hackathon_validation_error_missing_name(self, auth_client, mock_auth_user):
        """Should return 422 if required field 'name' is missing"""
        # Arrange
        invalid_payload = {**self.valid_payload}
        invalid_payload["organizer_id"] = mock_auth_user["id"]
        del invalid_payload["name"]

        # Act
        response = auth_client.post(
            "/api/v1/hackathons",
            json=invalid_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_hackathon_validation_error_name_too_short(self, auth_client, mock_auth_user):
        """Should return 422 if name is too short"""
        # Arrange
        invalid_payload = {
            **self.valid_payload,
            "organizer_id": mock_auth_user["id"],
            "name": "AB",  # Less than 3 characters
        }

        # Act
        response = auth_client.post(
            "/api/v1/hackathons",
            json=invalid_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("services.hackathon_service.create_hackathon")
    def test_create_hackathon_with_optional_fields(self, mock_create, auth_client, mock_auth_user):
        """Should successfully create hackathon with all optional fields"""
        # Arrange
        user_id = mock_auth_user["id"]
        full_payload = {
            **self.valid_payload,
            "organizer_id": user_id,
            "registration_deadline": (datetime.utcnow() + timedelta(days=20)).isoformat(),
            "max_participants": 150,
            "website_url": "https://hackathon2025.com",
            "prizes": {"first": "$10,000", "second": "$5,000"},
            "rules": "Standard hackathon rules apply",
        }

        hackathon_id = str(uuid.uuid4())
        mock_create.return_value = {
            "hackathon_id": hackathon_id,
            **HACKATHON_RESPONSE_DEFAULTS,
            **full_payload,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Act
        response = auth_client.post(
            "/api/v1/hackathons",
            json=full_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["max_participants"] == 150
        assert data["website_url"] == "https://hackathon2025.com"
        assert data["prizes"]["first"] == "$10,000"


class TestListHackathons:
    """Test GET /api/v1/hackathons endpoint"""

    @patch("services.hackathon_service.list_hackathons")
    def test_list_hackathons_success(self, mock_list, auth_client, mock_auth_user):
        """Should successfully list hackathons"""
        # Arrange
        hackathons = [
            _hackathon_response(
                hackathon_id=str(uuid.uuid4()),
                name="Hackathon 1",
                description="First hackathon",
                organizer_id=str(uuid.uuid4()),
                start_date=datetime.utcnow().isoformat(),
                end_date=(datetime.utcnow() + timedelta(days=2)).isoformat(),
                location="Virtual",
                status="active",
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
            ),
            _hackathon_response(
                hackathon_id=str(uuid.uuid4()),
                name="Hackathon 2",
                description="Second hackathon",
                organizer_id=str(uuid.uuid4()),
                start_date=datetime.utcnow().isoformat(),
                end_date=(datetime.utcnow() + timedelta(days=2)).isoformat(),
                location="San Francisco",
                status="upcoming",
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
            ),
        ]

        mock_list.return_value = {
            "hackathons": hackathons,
            "total": 2,
            "skip": 0,
            "limit": 100,
        }

        # Act
        response = auth_client.get(
            "/api/v1/hackathons",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert len(data["hackathons"]) == 2
        assert data["hackathons"][0]["name"] == "Hackathon 1"

    @patch("services.hackathon_service.list_hackathons")
    def test_list_hackathons_with_pagination(self, mock_list, auth_client, mock_auth_user):
        """Should list hackathons with pagination parameters"""
        # Arrange
        mock_list.return_value = {
            "hackathons": [],
            "total": 50,
            "skip": 10,
            "limit": 20,
        }

        # Act
        response = auth_client.get(
            "/api/v1/hackathons?skip=10&limit=20",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["skip"] == 10
        assert data["limit"] == 20
        mock_list.assert_called_once()

    @patch("services.hackathon_service.list_hackathons")
    def test_list_hackathons_with_status_filter(self, mock_list, auth_client, mock_auth_user):
        """Should filter hackathons by status"""
        # Arrange
        mock_list.return_value = {
            "hackathons": [],
            "total": 10,
            "skip": 0,
            "limit": 100,
        }

        # Act
        response = auth_client.get(
            "/api/v1/hackathons?status=active",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args[1]
        assert call_kwargs["status_filter"] == "active"

    def test_list_hackathons_unauthorized(self, unauth_client):
        """Should return 401 without authentication"""
        # Act
        response = unauth_client.get("/api/v1/hackathons")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_hackathons_validation_error_negative_skip(self, auth_client, mock_auth_user):
        """Should return 422 for negative skip value"""
        # Act
        response = auth_client.get(
            "/api/v1/hackathons?skip=-1",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetHackathon:
    """Test GET /api/v1/hackathons/{hackathon_id} endpoint"""

    @patch("services.hackathon_service.get_hackathon")
    def test_get_hackathon_success(self, mock_get, auth_client, mock_auth_user):
        """Should successfully get hackathon details"""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        hackathon = _hackathon_response(
            hackathon_id=hackathon_id,
            name="AI Hackathon 2025",
            description="Build AI apps",
            organizer_id=str(uuid.uuid4()),
            start_date=datetime.utcnow().isoformat(),
            end_date=(datetime.utcnow() + timedelta(days=2)).isoformat(),
            location="Virtual",
            status="active",
            max_participants=100,
            website_url="https://hackathon.com",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        mock_get.return_value = hackathon

        # Act
        response = auth_client.get(
            f"/api/v1/hackathons/{hackathon_id}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["hackathon_id"] == hackathon_id
        assert data["name"] == "AI Hackathon 2025"

    @patch("services.hackathon_service.get_hackathon")
    def test_get_hackathon_not_found(self, mock_get, auth_client, mock_auth_user):
        """Should return 404 if hackathon not found"""
        # Arrange
        from fastapi import HTTPException

        mock_get.side_effect = HTTPException(status_code=404, detail="Hackathon not found")

        # Act
        response = auth_client.get(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_hackathon_unauthorized(self, unauth_client):
        """Should return 401 without authentication"""
        # Act
        response = unauth_client.get(f"/api/v1/hackathons/{str(uuid.uuid4())}")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUpdateHackathon:
    """Test PATCH /api/v1/hackathons/{hackathon_id} endpoint"""

    @patch("services.hackathon_service.update_hackathon")
    def test_update_hackathon_success(self, mock_update, auth_client, mock_auth_user):
        """Should successfully update hackathon (ORGANIZER)"""
        # Arrange
        user_id = mock_auth_user["id"]
        hackathon_id = str(uuid.uuid4())

        update_payload = {
            "name": "Updated Hackathon Name",
            "status": "active",
            "max_participants": 200,
        }

        updated_hackathon = _hackathon_response(
            hackathon_id=hackathon_id,
            name="Updated Hackathon Name",
            description="Original description",
            organizer_id=user_id,
            start_date=datetime.utcnow().isoformat(),
            end_date=(datetime.utcnow() + timedelta(days=2)).isoformat(),
            location="Virtual",
            status="active",
            max_participants=200,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        mock_update.return_value = updated_hackathon

        # Act
        response = auth_client.patch(
            f"/api/v1/hackathons/{hackathon_id}",
            json=update_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Hackathon Name"
        assert data["status"] == "active"
        assert data["max_participants"] == 200

    @patch("services.hackathon_service.update_hackathon")
    def test_update_hackathon_forbidden_not_organizer(self, mock_update, auth_client, mock_auth_user):
        """Should return 403 if user is not ORGANIZER"""
        # Arrange
        from fastapi import HTTPException

        mock_update.side_effect = HTTPException(
            status_code=403, detail="User does not have ORGANIZER role"
        )

        # Act
        response = auth_client.patch(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            json={"name": "Updated Name"},
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_hackathon_validation_error_no_fields(self, auth_client, mock_auth_user):
        """Should return 400 if no fields provided for update"""
        # Act
        response = auth_client.patch(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            json={},
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_hackathon_unauthorized(self, unauth_client):
        """Should return 401 without authentication"""
        # Act
        response = unauth_client.patch(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            json={"name": "Updated"},
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeleteHackathon:
    """Test DELETE /api/v1/hackathons/{hackathon_id} endpoint"""

    @patch("services.hackathon_service.delete_hackathon")
    def test_delete_hackathon_success(self, mock_delete, auth_client, mock_auth_user):
        """Should successfully delete hackathon (ORGANIZER, soft delete)"""
        # Arrange
        hackathon_id = str(uuid.uuid4())

        mock_delete.return_value = {
            "success": True,
            "hackathon_id": hackathon_id,
            "message": "Hackathon successfully deleted",
        }

        # Act
        response = auth_client.delete(
            f"/api/v1/hackathons/{hackathon_id}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["hackathon_id"] == hackathon_id
        assert "successfully deleted" in data["message"]

    @patch("services.hackathon_service.delete_hackathon")
    def test_delete_hackathon_forbidden_not_organizer(self, mock_delete, auth_client, mock_auth_user):
        """Should return 403 if user is not ORGANIZER"""
        # Arrange
        from fastapi import HTTPException

        mock_delete.side_effect = HTTPException(
            status_code=403, detail="User does not have ORGANIZER role"
        )

        # Act
        response = auth_client.delete(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("services.hackathon_service.delete_hackathon")
    def test_delete_hackathon_not_found(self, mock_delete, auth_client, mock_auth_user):
        """Should return 404 if hackathon not found"""
        # Arrange
        from fastapi import HTTPException

        mock_delete.side_effect = HTTPException(
            status_code=404, detail="Hackathon not found"
        )

        # Act
        response = auth_client.delete(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_hackathon_unauthorized(self, unauth_client):
        """Should return 401 without authentication"""
        # Act
        response = unauth_client.delete(f"/api/v1/hackathons/{str(uuid.uuid4())}")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestHackathonEndpointsIntegration:
    """Integration tests for hackathon endpoints workflow"""

    @patch("services.hackathon_service.create_hackathon")
    @patch("services.hackathon_service.get_hackathon")
    @patch("services.hackathon_service.update_hackathon")
    @patch("services.hackathon_service.delete_hackathon")
    def test_full_hackathon_lifecycle(
        self,
        mock_delete,
        mock_update,
        mock_get,
        mock_create,
        auth_client,
        mock_auth_user,
    ):
        """Should test complete hackathon lifecycle: create -> get -> update -> delete"""
        # Arrange
        user_id = mock_auth_user["id"]
        hackathon_id = str(uuid.uuid4())

        # Step 1: Create
        create_payload = {
            "name": "Test Hackathon",
            "description": "Test description",
            "organizer_id": user_id,
            "start_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=32)).isoformat(),
            "location": "Virtual",
            "status": "draft",
        }

        created_hackathon = _hackathon_response(
            hackathon_id=hackathon_id,
            **create_payload,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        mock_create.return_value = created_hackathon

        create_response = auth_client.post(
            "/api/v1/hackathons",
            json=create_payload,
            headers={"Authorization": "Bearer fake-token"},
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        # Step 2: Get
        mock_get.return_value = created_hackathon
        get_response = auth_client.get(
            f"/api/v1/hackathons/{hackathon_id}",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert get_response.status_code == status.HTTP_200_OK

        # Step 3: Update
        updated_hackathon = {**created_hackathon, "status": "active"}
        mock_update.return_value = updated_hackathon
        update_response = auth_client.patch(
            f"/api/v1/hackathons/{hackathon_id}",
            json={"status": "active"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert update_response.status_code == status.HTTP_200_OK

        # Step 4: Delete
        mock_delete.return_value = {
            "success": True,
            "hackathon_id": hackathon_id,
            "message": "Hackathon successfully deleted",
        }
        delete_response = auth_client.delete(
            f"/api/v1/hackathons/{hackathon_id}",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert delete_response.status_code == status.HTTP_200_OK
