"""
Tests for Submission API Endpoints

Following TDD methodology - comprehensive tests for submission CRUD
operations and file upload functionality.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.dependencies import get_current_user
from api.routes.submissions import router
from fastapi import status
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def mock_user():
    """Mock authenticated user for testing."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User",
        "role": "ADMIN",
        "email_verified": True,
    }


@pytest.fixture
def auth_client(mock_user):
    """Test client with auth and zerodb dependencies overridden."""
    from api.routes.submissions import get_zerodb_client
    from unittest.mock import MagicMock

    async def override_auth():
        return mock_user

    def override_zerodb():
        return MagicMock()

    app.dependency_overrides[get_current_user] = override_auth
    app.dependency_overrides[get_zerodb_client] = override_zerodb
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_zerodb_client, None)


@pytest.fixture
def mock_submission_data():
    """Mock submission data for testing."""
    return {
        "submission_id": str(uuid.uuid4()),
        "team_id": str(uuid.uuid4()),
        "hackathon_id": str(uuid.uuid4()),
        "project_name": "AI Code Assistant",
        "description": "An intelligent code completion tool powered by ML",
        "repository_url": "https://github.com/team/project",
        "demo_url": "https://demo.example.com",
        "video_url": "https://youtube.com/watch?v=demo",
        "status": "DRAFT",
        "files": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "submitted_at": None,
    }


@pytest.fixture
def mock_zerodb_client():
    """Mock ZeroDB client for testing."""
    client = AsyncMock()
    client.tables = AsyncMock()
    client.files = AsyncMock()
    return client


class TestCreateSubmission:
    """Test POST /v1/submissions endpoint"""

    @patch("api.routes.submissions.create_submission")
    def test_create_submission_success(
        self, mock_create, auth_client, mock_user, mock_submission_data
    ):
        """Should create submission and return 201"""
        # Arrange
        mock_create.return_value = mock_submission_data

        request_data = {
            "team_id": mock_submission_data["team_id"],
            "hackathon_id": mock_submission_data["hackathon_id"],
            "project_name": "AI Code Assistant",
            "description": "An intelligent code completion tool",
            "repository_url": "https://github.com/team/project",
        }

        # Act
        response = auth_client.post(
            "/v1/submissions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["project_name"] == "AI Code Assistant"
        assert data["status"] == "DRAFT"

    def test_create_submission_missing_required_fields(self, auth_client, mock_user):
        """Should return 422 for missing required fields"""
        # Arrange
        request_data = {
            "team_id": str(uuid.uuid4()),
            # Missing hackathon_id, project_name, description
        }

        # Act
        response = auth_client.post(
            "/v1/submissions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("api.routes.submissions.create_submission")
    def test_create_submission_team_not_found(
        self, mock_create, auth_client, mock_user
    ):
        """Should return 404 when team doesn't exist"""
        # Arrange
        from fastapi import HTTPException

        mock_create.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

        request_data = {
            "team_id": str(uuid.uuid4()),
            "hackathon_id": str(uuid.uuid4()),
            "project_name": "Test Project",
            "description": "Test description with enough text",
        }

        # Act
        response = auth_client.post(
            "/v1/submissions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_submission_unauthorized(self):
        """Should return 401 without authentication"""
        # Arrange
        request_data = {
            "team_id": str(uuid.uuid4()),
            "hackathon_id": str(uuid.uuid4()),
            "project_name": "Test Project",
            "description": "Test description",
        }

        # Act - use client without overrides
        app.dependency_overrides.pop(get_current_user, None)
        client = TestClient(app)
        response = client.post("/v1/submissions", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListSubmissions:
    """Test GET /v1/submissions endpoint"""

    @patch("api.routes.submissions.list_submissions")
    def test_list_submissions_success(
        self, mock_list, auth_client, mock_user, mock_submission_data
    ):
        """Should list submissions and return 200"""
        # Arrange
        mock_list.return_value = [mock_submission_data]

        # Act
        response = auth_client.get(
            "/v1/submissions", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "submissions" in data
        assert len(data["submissions"]) == 1
        assert data["total"] == 1

    @patch("api.routes.submissions.list_submissions")
    def test_list_submissions_with_filters(
        self, mock_list, auth_client, mock_user, mock_submission_data
    ):
        """Should filter submissions by hackathon and status"""
        # Arrange
        mock_list.return_value = [mock_submission_data]
        hackathon_id = str(uuid.uuid4())

        # Act
        response = auth_client.get(
            f"/v1/submissions?hackathon_id={hackathon_id}&status=SUBMITTED",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args[1]
        assert call_kwargs["hackathon_id"] == hackathon_id
        assert call_kwargs["status"] == "SUBMITTED"

    def test_list_submissions_invalid_status(self, auth_client, mock_user):
        """Should return 400 for invalid status filter"""
        # Act
        response = auth_client.get(
            "/v1/submissions?status=INVALID",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.routes.submissions.list_submissions")
    def test_list_submissions_pagination(
        self, mock_list, auth_client, mock_user
    ):
        """Should support pagination parameters"""
        # Arrange
        mock_list.return_value = []

        # Act
        response = auth_client.get(
            "/v1/submissions?skip=10&limit=20",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args[1]
        assert call_kwargs["skip"] == 10
        assert call_kwargs["limit"] == 20


class TestGetSubmission:
    """Test GET /v1/submissions/{id} endpoint"""

    @patch("api.routes.submissions.get_submission")
    def test_get_submission_success(
        self, mock_get, auth_client, mock_user, mock_submission_data
    ):
        """Should get submission by ID and return 200"""
        # Arrange
        mock_get.return_value = mock_submission_data
        submission_id = mock_submission_data["submission_id"]

        # Act
        response = auth_client.get(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["submission_id"] == submission_id
        assert data["project_name"] == "AI Code Assistant"

    @patch("api.routes.submissions.get_submission")
    def test_get_submission_not_found(
        self, mock_get, auth_client, mock_user
    ):
        """Should return 404 when submission doesn't exist"""
        # Arrange
        from fastapi import HTTPException

        mock_get.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
        submission_id = str(uuid.uuid4())

        # Act
        response = auth_client.get(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_submission_invalid_uuid(self, auth_client):
        """Should return 422 for invalid UUID format"""
        # Act
        response = auth_client.get(
            "/v1/submissions/invalid-uuid",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpdateSubmission:
    """Test PUT /v1/submissions/{id} endpoint"""

    @patch("api.routes.submissions.update_submission")
    def test_update_submission_success(
        self, mock_update, auth_client, mock_user, mock_submission_data
    ):
        """Should update submission and return 200"""
        # Arrange
        updated_data = mock_submission_data.copy()
        updated_data["project_name"] = "Updated Project Name"
        updated_data["status"] = "SUBMITTED"
        mock_update.return_value = updated_data
        submission_id = mock_submission_data["submission_id"]

        update_request = {
            "project_name": "Updated Project Name",
            "status": "SUBMITTED",
        }

        # Act
        response = auth_client.put(
            f"/v1/submissions/{submission_id}",
            json=update_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_name"] == "Updated Project Name"
        assert data["status"] == "SUBMITTED"

    @patch("api.routes.submissions.update_submission")
    def test_update_submission_partial(
        self, mock_update, auth_client, mock_user, mock_submission_data
    ):
        """Should allow partial updates"""
        # Arrange
        updated_data = mock_submission_data.copy()
        updated_data["description"] = "New description"
        mock_update.return_value = updated_data
        submission_id = mock_submission_data["submission_id"]

        update_request = {"description": "New description"}

        # Act
        response = auth_client.put(
            f"/v1/submissions/{submission_id}",
            json=update_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    @patch("api.routes.submissions.update_submission")
    def test_update_submission_not_found(
        self, mock_update, auth_client, mock_user
    ):
        """Should return 404 when submission doesn't exist"""
        # Arrange
        from fastapi import HTTPException

        mock_update.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
        submission_id = str(uuid.uuid4())

        # Act
        response = auth_client.put(
            f"/v1/submissions/{submission_id}",
            json={"project_name": "Updated Name"},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_submission_invalid_status(self, auth_client, mock_user):
        """Should return 422 for invalid status value"""
        # Arrange
        submission_id = str(uuid.uuid4())

        # Act
        response = auth_client.put(
            f"/v1/submissions/{submission_id}",
            json={"status": "INVALID_STATUS"},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteSubmission:
    """Test DELETE /v1/submissions/{id} endpoint"""

    @patch("api.routes.submissions.delete_submission")
    def test_delete_submission_success(
        self, mock_delete, auth_client, mock_user
    ):
        """Should delete submission and return 204"""
        # Arrange
        mock_delete.return_value = {"success": True}
        submission_id = str(uuid.uuid4())

        # Act
        response = auth_client.delete(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch("api.routes.submissions.delete_submission")
    def test_delete_submission_not_found(
        self, mock_delete, auth_client, mock_user
    ):
        """Should return 404 when submission doesn't exist"""
        # Arrange
        from fastapi import HTTPException

        mock_delete.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
        submission_id = str(uuid.uuid4())

        # Act
        response = auth_client.delete(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.submissions.delete_submission")
    def test_delete_submission_already_scored(
        self, mock_delete, auth_client, mock_user
    ):
        """Should return 400 when trying to delete SCORED submission"""
        # Arrange
        from fastapi import HTTPException

        mock_delete.side_effect = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a submission that has been scored",
        )
        submission_id = str(uuid.uuid4())

        # Act
        response = auth_client.delete(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestFileUpload:
    """Test POST /v1/submissions/{id}/files endpoint"""

    @patch("api.routes.submissions.upload_file_to_submission")
    def test_upload_file_success(
        self, mock_upload, auth_client, mock_user
    ):
        """Should upload file and return 201"""
        # Arrange
        file_metadata = {
            "file_id": str(uuid.uuid4()),
            "file_name": "presentation.pdf",
            "file_url": "https://storage.example.com/files/abc123",
            "file_type": "application/pdf",
            "file_size": 2048576,
            "uploaded_at": datetime.utcnow().isoformat(),
        }
        mock_upload.return_value = file_metadata
        submission_id = str(uuid.uuid4())

        file_request = {
            "file_name": "presentation.pdf",
            "file_type": "application/pdf",
            "file_size": 2048576,
            "file_content": "JVBERi0xLjQKJeLjz9MK...",  # Base64 PDF header
        }

        # Act
        response = auth_client.post(
            f"/v1/submissions/{submission_id}/files",
            json=file_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["file_name"] == "presentation.pdf"
        assert data["file_type"] == "application/pdf"

    @patch("api.routes.submissions.upload_file_to_submission")
    def test_upload_file_submission_not_found(
        self, mock_upload, auth_client, mock_user
    ):
        """Should return 404 when submission doesn't exist"""
        # Arrange
        from fastapi import HTTPException

        mock_upload.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
        submission_id = str(uuid.uuid4())

        file_request = {
            "file_name": "test.pdf",
            "file_type": "application/pdf",
            "file_size": 1024,
            "file_content": "base64content",
        }

        # Act
        response = auth_client.post(
            f"/v1/submissions/{submission_id}/files",
            json=file_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_upload_file_too_large(self, auth_client, mock_user):
        """Should return 422 for files exceeding 100MB"""
        # Arrange
        submission_id = str(uuid.uuid4())

        file_request = {
            "file_name": "huge.pdf",
            "file_type": "application/pdf",
            "file_size": 200_000_000,  # 200MB (exceeds 100MB limit)
            "file_content": "base64content",
        }

        # Act
        response = auth_client.post(
            f"/v1/submissions/{submission_id}/files",
            json=file_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_file_invalid_mime_type(self, auth_client, mock_user):
        """Should return 422 for invalid MIME type format"""
        # Arrange
        submission_id = str(uuid.uuid4())

        file_request = {
            "file_name": "test.pdf",
            "file_type": "invalid-mime",  # Missing '/' separator
            "file_size": 1024,
            "file_content": "base64content",
        }

        # Act
        response = auth_client.post(
            f"/v1/submissions/{submission_id}/files",
            json=file_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
