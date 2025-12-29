"""
Tests for Hackathon API Endpoints

Comprehensive test suite for hackathon CRUD endpoints with authentication,
authorization, validation, and error handling.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from api.routes.hackathons import router
from fastapi import status
from fastapi.testclient import TestClient
from main import app


# Test client
client = TestClient(app)


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

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.create_hackathon")
    def test_create_hackathon_success(
        self, mock_create, mock_zerodb, mock_auth
    ):
        """Should successfully create hackathon"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        self.valid_payload["organizer_id"] = user_id

        hackathon_id = str(uuid.uuid4())
        mock_create.return_value = {
            "hackathon_id": hackathon_id,
            **self.valid_payload,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Act
        response = client.post(
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

    @patch("api.routes.hackathons.get_current_user")
    def test_create_hackathon_unauthorized(self, mock_auth):
        """Should return 401 without authentication"""
        # Act
        response = client.post("/api/v1/hackathons", json=self.valid_payload)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("api.routes.hackathons.get_current_user")
    def test_create_hackathon_forbidden_organizer_mismatch(self, mock_auth):
        """Should return 403 if organizer_id doesn't match authenticated user"""
        # Arrange
        user_id = str(uuid.uuid4())
        different_user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        self.valid_payload["organizer_id"] = different_user_id

        # Act
        response = client.post(
            "/api/v1/hackathons",
            json=self.valid_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "organizer_id must match" in response.json()["detail"]

    @patch("api.routes.hackathons.get_current_user")
    def test_create_hackathon_validation_error_end_before_start(self, mock_auth):
        """Should return 400 if end_date is before start_date"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        invalid_payload = {
            **self.valid_payload,
            "organizer_id": user_id,
            "start_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=25)).isoformat(),  # Before start
        }

        # Act
        response = client.post(
            "/api/v1/hackathons",
            json=invalid_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("api.routes.hackathons.get_current_user")
    def test_create_hackathon_validation_error_missing_name(self, mock_auth):
        """Should return 422 if required field 'name' is missing"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        invalid_payload = {**self.valid_payload}
        del invalid_payload["name"]

        # Act
        response = client.post(
            "/api/v1/hackathons",
            json=invalid_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("api.routes.hackathons.get_current_user")
    def test_create_hackathon_validation_error_name_too_short(self, mock_auth):
        """Should return 422 if name is too short"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        invalid_payload = {
            **self.valid_payload,
            "organizer_id": user_id,
            "name": "AB",  # Less than 3 characters
        }

        # Act
        response = client.post(
            "/api/v1/hackathons",
            json=invalid_payload,
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.create_hackathon")
    def test_create_hackathon_with_optional_fields(
        self, mock_create, mock_zerodb, mock_auth
    ):
        """Should successfully create hackathon with all optional fields"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
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
            **full_payload,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Act
        response = client.post(
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

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.list_hackathons")
    def test_list_hackathons_success(self, mock_list, mock_zerodb, mock_auth):
        """Should successfully list hackathons"""
        # Arrange
        mock_auth.return_value = {"id": str(uuid.uuid4())}
        hackathons = [
            {
                "hackathon_id": str(uuid.uuid4()),
                "name": "Hackathon 1",
                "description": "First hackathon",
                "organizer_id": str(uuid.uuid4()),
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
                "location": "Virtual",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            {
                "hackathon_id": str(uuid.uuid4()),
                "name": "Hackathon 2",
                "description": "Second hackathon",
                "organizer_id": str(uuid.uuid4()),
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
                "location": "San Francisco",
                "status": "upcoming",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        ]

        mock_list.return_value = {
            "hackathons": hackathons,
            "total": 2,
            "skip": 0,
            "limit": 100,
        }

        # Act
        response = client.get(
            "/api/v1/hackathons",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert len(data["hackathons"]) == 2
        assert data["hackathons"][0]["name"] == "Hackathon 1"

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.list_hackathons")
    def test_list_hackathons_with_pagination(self, mock_list, mock_zerodb, mock_auth):
        """Should list hackathons with pagination parameters"""
        # Arrange
        mock_auth.return_value = {"id": str(uuid.uuid4())}
        mock_list.return_value = {
            "hackathons": [],
            "total": 50,
            "skip": 10,
            "limit": 20,
        }

        # Act
        response = client.get(
            "/api/v1/hackathons?skip=10&limit=20",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["skip"] == 10
        assert data["limit"] == 20
        mock_list.assert_called_once()

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.list_hackathons")
    def test_list_hackathons_with_status_filter(self, mock_list, mock_zerodb, mock_auth):
        """Should filter hackathons by status"""
        # Arrange
        mock_auth.return_value = {"id": str(uuid.uuid4())}
        mock_list.return_value = {
            "hackathons": [],
            "total": 10,
            "skip": 0,
            "limit": 100,
        }

        # Act
        response = client.get(
            "/api/v1/hackathons?status=active",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args[1]
        assert call_kwargs["status_filter"] == "active"

    @patch("api.routes.hackathons.get_current_user")
    def test_list_hackathons_unauthorized(self, mock_auth):
        """Should return 401 without authentication"""
        # Act
        response = client.get("/api/v1/hackathons")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("api.routes.hackathons.get_current_user")
    def test_list_hackathons_validation_error_negative_skip(self, mock_auth):
        """Should return 422 for negative skip value"""
        # Arrange
        mock_auth.return_value = {"id": str(uuid.uuid4())}

        # Act
        response = client.get(
            "/api/v1/hackathons?skip=-1",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetHackathon:
    """Test GET /api/v1/hackathons/{hackathon_id} endpoint"""

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.get_hackathon")
    def test_get_hackathon_success(self, mock_get, mock_zerodb, mock_auth):
        """Should successfully get hackathon details"""
        # Arrange
        mock_auth.return_value = {"id": str(uuid.uuid4())}
        hackathon_id = str(uuid.uuid4())
        hackathon = {
            "hackathon_id": hackathon_id,
            "name": "AI Hackathon 2025",
            "description": "Build AI apps",
            "organizer_id": str(uuid.uuid4()),
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "location": "Virtual",
            "status": "active",
            "max_participants": 100,
            "website_url": "https://hackathon.com",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        mock_get.return_value = hackathon

        # Act
        response = client.get(
            f"/api/v1/hackathons/{hackathon_id}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["hackathon_id"] == hackathon_id
        assert data["name"] == "AI Hackathon 2025"

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.get_hackathon")
    def test_get_hackathon_not_found(self, mock_get, mock_zerodb, mock_auth):
        """Should return 404 if hackathon not found"""
        # Arrange
        mock_auth.return_value = {"id": str(uuid.uuid4())}
        from fastapi import HTTPException

        mock_get.side_effect = HTTPException(status_code=404, detail="Hackathon not found")

        # Act
        response = client.get(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.hackathons.get_current_user")
    def test_get_hackathon_unauthorized(self, mock_auth):
        """Should return 401 without authentication"""
        # Act
        response = client.get(f"/api/v1/hackathons/{str(uuid.uuid4())}")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUpdateHackathon:
    """Test PATCH /api/v1/hackathons/{hackathon_id} endpoint"""

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.update_hackathon")
    def test_update_hackathon_success(self, mock_update, mock_zerodb, mock_auth):
        """Should successfully update hackathon (ORGANIZER)"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        hackathon_id = str(uuid.uuid4())

        update_payload = {
            "name": "Updated Hackathon Name",
            "status": "active",
            "max_participants": 200,
        }

        updated_hackathon = {
            "hackathon_id": hackathon_id,
            "name": "Updated Hackathon Name",
            "description": "Original description",
            "organizer_id": user_id,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "location": "Virtual",
            "status": "active",
            "max_participants": 200,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        mock_update.return_value = updated_hackathon

        # Act
        response = client.patch(
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

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.update_hackathon")
    def test_update_hackathon_forbidden_not_organizer(
        self, mock_update, mock_zerodb, mock_auth
    ):
        """Should return 403 if user is not ORGANIZER"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        from fastapi import HTTPException

        mock_update.side_effect = HTTPException(
            status_code=403, detail="User does not have ORGANIZER role"
        )

        # Act
        response = client.patch(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            json={"name": "Updated Name"},
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("api.routes.hackathons.get_current_user")
    def test_update_hackathon_validation_error_no_fields(self, mock_auth):
        """Should return 400 if no fields provided for update"""
        # Arrange
        mock_auth.return_value = {"id": str(uuid.uuid4())}

        # Act
        response = client.patch(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            json={},
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.routes.hackathons.get_current_user")
    def test_update_hackathon_unauthorized(self, mock_auth):
        """Should return 401 without authentication"""
        # Act
        response = client.patch(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            json={"name": "Updated"},
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeleteHackathon:
    """Test DELETE /api/v1/hackathons/{hackathon_id} endpoint"""

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.delete_hackathon")
    def test_delete_hackathon_success(self, mock_delete, mock_zerodb, mock_auth):
        """Should successfully delete hackathon (ORGANIZER, soft delete)"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        hackathon_id = str(uuid.uuid4())

        mock_delete.return_value = {
            "success": True,
            "hackathon_id": hackathon_id,
            "message": "Hackathon successfully deleted",
        }

        # Act
        response = client.delete(
            f"/api/v1/hackathons/{hackathon_id}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["hackathon_id"] == hackathon_id
        assert "successfully deleted" in data["message"]

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.delete_hackathon")
    def test_delete_hackathon_forbidden_not_organizer(
        self, mock_delete, mock_zerodb, mock_auth
    ):
        """Should return 403 if user is not ORGANIZER"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        from fastapi import HTTPException

        mock_delete.side_effect = HTTPException(
            status_code=403, detail="User does not have ORGANIZER role"
        )

        # Act
        response = client.delete(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
    @patch("services.hackathon_service.delete_hackathon")
    def test_delete_hackathon_not_found(self, mock_delete, mock_zerodb, mock_auth):
        """Should return 404 if hackathon not found"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
        from fastapi import HTTPException

        mock_delete.side_effect = HTTPException(
            status_code=404, detail="Hackathon not found"
        )

        # Act
        response = client.delete(
            f"/api/v1/hackathons/{str(uuid.uuid4())}",
            headers={"Authorization": "Bearer fake-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.hackathons.get_current_user")
    def test_delete_hackathon_unauthorized(self, mock_auth):
        """Should return 401 without authentication"""
        # Act
        response = client.delete(f"/api/v1/hackathons/{str(uuid.uuid4())}")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestHackathonEndpointsIntegration:
    """Integration tests for hackathon endpoints workflow"""

    @patch("api.routes.hackathons.get_current_user")
    @patch("api.routes.hackathons.get_zerodb_client")
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
        mock_zerodb,
        mock_auth,
    ):
        """Should test complete hackathon lifecycle: create → get → update → delete"""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_auth.return_value = {"id": user_id}
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

        created_hackathon = {
            "hackathon_id": hackathon_id,
            **create_payload,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        mock_create.return_value = created_hackathon

        create_response = client.post(
            "/api/v1/hackathons",
            json=create_payload,
            headers={"Authorization": "Bearer fake-token"},
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        # Step 2: Get
        mock_get.return_value = created_hackathon
        get_response = client.get(
            f"/api/v1/hackathons/{hackathon_id}",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert get_response.status_code == status.HTTP_200_OK

        # Step 3: Update
        updated_hackathon = {**created_hackathon, "status": "active"}
        mock_update.return_value = updated_hackathon
        update_response = client.patch(
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
        delete_response = client.delete(
            f"/api/v1/hackathons/{hackathon_id}",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert delete_response.status_code == status.HTTP_200_OK
