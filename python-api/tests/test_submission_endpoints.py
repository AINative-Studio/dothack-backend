"""
Tests for Submission API Endpoints

Following TDD methodology - comprehensive tests for submission CRUD
operations and file upload functionality.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.routes.submissions import router
from fastapi import status
from fastapi.testclient import TestClient


@pytest.fixture
def mock_user():
    """Mock authenticated user for testing."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User",
        "email_verified": True,
    }


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

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.create_submission")
    async def test_create_submission_success(
        self, mock_create, mock_get_client, mock_get_user, mock_user, mock_submission_data
    ):
        """Should create submission and return 201"""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_create.return_value = mock_submission_data

        request_data = {
            "team_id": mock_submission_data["team_id"],
            "hackathon_id": mock_submission_data["hackathon_id"],
            "project_name": "AI Code Assistant",
            "description": "An intelligent code completion tool",
            "repository_url": "https://github.com/team/project",
        }

        # Act
        from main import app

        client = TestClient(app)
        response = client.post(
            "/v1/submissions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["project_name"] == "AI Code Assistant"
        assert data["status"] == "DRAFT"

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    async def test_create_submission_missing_required_fields(self, mock_get_user, mock_user):
        """Should return 422 for missing required fields"""
        # Arrange
        mock_get_user.return_value = mock_user
        request_data = {
            "team_id": str(uuid.uuid4()),
            # Missing hackathon_id, project_name, description
        }

        # Act
        from main import app

        client = TestClient(app)
        response = client.post(
            "/v1/submissions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.create_submission")
    async def test_create_submission_team_not_found(
        self, mock_create, mock_get_client, mock_get_user, mock_user
    ):
        """Should return 404 when team doesn't exist"""
        # Arrange
        mock_get_user.return_value = mock_user
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
        from main import app

        client = TestClient(app)
        response = client.post(
            "/v1/submissions",
            json=request_data,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_submission_unauthorized(self):
        """Should return 401 without authentication"""
        # Arrange
        request_data = {
            "team_id": str(uuid.uuid4()),
            "hackathon_id": str(uuid.uuid4()),
            "project_name": "Test Project",
            "description": "Test description",
        }

        # Act
        from main import app

        client = TestClient(app)
        response = client.post("/v1/submissions", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListSubmissions:
    """Test GET /v1/submissions endpoint"""

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.list_submissions")
    async def test_list_submissions_success(
        self, mock_list, mock_get_client, mock_get_user, mock_user, mock_submission_data
    ):
        """Should list submissions and return 200"""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_list.return_value = [mock_submission_data]

        # Act
        from main import app

        client = TestClient(app)
        response = client.get(
            "/v1/submissions", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "submissions" in data
        assert len(data["submissions"]) == 1
        assert data["total"] == 1

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.list_submissions")
    async def test_list_submissions_with_filters(
        self, mock_list, mock_get_client, mock_get_user, mock_user, mock_submission_data
    ):
        """Should filter submissions by hackathon and status"""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_list.return_value = [mock_submission_data]
        hackathon_id = str(uuid.uuid4())

        # Act
        from main import app

        client = TestClient(app)
        response = client.get(
            f"/v1/submissions?hackathon_id={hackathon_id}&status=SUBMITTED",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args[1]
        assert call_kwargs["hackathon_id"] == hackathon_id
        assert call_kwargs["status"] == "SUBMITTED"

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    async def test_list_submissions_invalid_status(self, mock_get_user, mock_user):
        """Should return 400 for invalid status filter"""
        # Arrange
        mock_get_user.return_value = mock_user

        # Act
        from main import app

        client = TestClient(app)
        response = client.get(
            "/v1/submissions?status=INVALID",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.list_submissions")
    async def test_list_submissions_pagination(
        self, mock_list, mock_get_client, mock_get_user, mock_user
    ):
        """Should support pagination parameters"""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_list.return_value = []

        # Act
        from main import app

        client = TestClient(app)
        response = client.get(
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

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.get_submission")
    async def test_get_submission_success(
        self, mock_get, mock_get_client, mock_get_user, mock_user, mock_submission_data
    ):
        """Should get submission by ID and return 200"""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_get.return_value = mock_submission_data
        submission_id = mock_submission_data["submission_id"]

        # Act
        from main import app

        client = TestClient(app)
        response = client.get(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["submission_id"] == submission_id
        assert data["project_name"] == "AI Code Assistant"

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.get_submission")
    async def test_get_submission_not_found(
        self, mock_get, mock_get_client, mock_get_user, mock_user
    ):
        """Should return 404 when submission doesn't exist"""
        # Arrange
        mock_get_user.return_value = mock_user
        from fastapi import HTTPException

        mock_get.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
        submission_id = str(uuid.uuid4())

        # Act
        from main import app

        client = TestClient(app)
        response = client.get(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_submission_invalid_uuid(self):
        """Should return 422 for invalid UUID format"""
        # Act
        from main import app

        client = TestClient(app)
        response = client.get(
            "/v1/submissions/invalid-uuid",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpdateSubmission:
    """Test PUT /v1/submissions/{id} endpoint"""

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.update_submission")
    async def test_update_submission_success(
        self, mock_update, mock_get_client, mock_get_user, mock_user, mock_submission_data
    ):
        """Should update submission and return 200"""
        # Arrange
        mock_get_user.return_value = mock_user
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
        from main import app

        client = TestClient(app)
        response = client.put(
            f"/v1/submissions/{submission_id}",
            json=update_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["project_name"] == "Updated Project Name"
        assert data["status"] == "SUBMITTED"

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.update_submission")
    async def test_update_submission_partial(
        self, mock_update, mock_get_client, mock_get_user, mock_user, mock_submission_data
    ):
        """Should allow partial updates"""
        # Arrange
        mock_get_user.return_value = mock_user
        updated_data = mock_submission_data.copy()
        updated_data["description"] = "New description"
        mock_update.return_value = updated_data
        submission_id = mock_submission_data["submission_id"]

        update_request = {"description": "New description"}

        # Act
        from main import app

        client = TestClient(app)
        response = client.put(
            f"/v1/submissions/{submission_id}",
            json=update_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.update_submission")
    async def test_update_submission_not_found(
        self, mock_update, mock_get_client, mock_get_user, mock_user
    ):
        """Should return 404 when submission doesn't exist"""
        # Arrange
        mock_get_user.return_value = mock_user
        from fastapi import HTTPException

        mock_update.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
        submission_id = str(uuid.uuid4())

        # Act
        from main import app

        client = TestClient(app)
        response = client.put(
            f"/v1/submissions/{submission_id}",
            json={"project_name": "Updated Name"},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    async def test_update_submission_invalid_status(self, mock_get_user, mock_user):
        """Should return 400 for invalid status value"""
        # Arrange
        mock_get_user.return_value = mock_user
        submission_id = str(uuid.uuid4())

        # Act
        from main import app

        client = TestClient(app)
        response = client.put(
            f"/v1/submissions/{submission_id}",
            json={"status": "INVALID_STATUS"},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteSubmission:
    """Test DELETE /v1/submissions/{id} endpoint"""

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.delete_submission")
    async def test_delete_submission_success(
        self, mock_delete, mock_get_client, mock_get_user, mock_user
    ):
        """Should delete submission and return 204"""
        # Arrange
        mock_get_user.return_value = mock_user
        mock_delete.return_value = {"success": True}
        submission_id = str(uuid.uuid4())

        # Act
        from main import app

        client = TestClient(app)
        response = client.delete(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.delete_submission")
    async def test_delete_submission_not_found(
        self, mock_delete, mock_get_client, mock_get_user, mock_user
    ):
        """Should return 404 when submission doesn't exist"""
        # Arrange
        mock_get_user.return_value = mock_user
        from fastapi import HTTPException

        mock_delete.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
        submission_id = str(uuid.uuid4())

        # Act
        from main import app

        client = TestClient(app)
        response = client.delete(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.delete_submission")
    async def test_delete_submission_already_scored(
        self, mock_delete, mock_get_client, mock_get_user, mock_user
    ):
        """Should return 400 when trying to delete SCORED submission"""
        # Arrange
        mock_get_user.return_value = mock_user
        from fastapi import HTTPException

        mock_delete.side_effect = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a submission that has been scored",
        )
        submission_id = str(uuid.uuid4())

        # Act
        from main import app

        client = TestClient(app)
        response = client.delete(
            f"/v1/submissions/{submission_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestFileUpload:
    """Test POST /v1/submissions/{id}/files endpoint"""

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.upload_file_to_submission")
    async def test_upload_file_success(
        self, mock_upload, mock_get_client, mock_get_user, mock_user
    ):
        """Should upload file and return 201"""
        # Arrange
        mock_get_user.return_value = mock_user
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
        from main import app

        client = TestClient(app)
        response = client.post(
            f"/v1/submissions/{submission_id}/files",
            json=file_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["file_name"] == "presentation.pdf"
        assert data["file_type"] == "application/pdf"

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    @patch("api.routes.submissions.get_zerodb_client")
    @patch("services.submission_service.upload_file_to_submission")
    async def test_upload_file_submission_not_found(
        self, mock_upload, mock_get_client, mock_get_user, mock_user
    ):
        """Should return 404 when submission doesn't exist"""
        # Arrange
        mock_get_user.return_value = mock_user
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
        from main import app

        client = TestClient(app)
        response = client.post(
            f"/v1/submissions/{submission_id}/files",
            json=file_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    async def test_upload_file_too_large(self, mock_get_user, mock_user):
        """Should return 422 for files exceeding 100MB"""
        # Arrange
        mock_get_user.return_value = mock_user
        submission_id = str(uuid.uuid4())

        file_request = {
            "file_name": "huge.pdf",
            "file_type": "application/pdf",
            "file_size": 200_000_000,  # 200MB (exceeds 100MB limit)
            "file_content": "base64content",
        }

        # Act
        from main import app

        client = TestClient(app)
        response = client.post(
            f"/v1/submissions/{submission_id}/files",
            json=file_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @patch("api.routes.submissions.get_current_user")
    async def test_upload_file_invalid_mime_type(self, mock_get_user, mock_user):
        """Should return 422 for invalid MIME type format"""
        # Arrange
        mock_get_user.return_value = mock_user
        submission_id = str(uuid.uuid4())

        file_request = {
            "file_name": "test.pdf",
            "file_type": "invalid-mime",  # Missing '/' separator
            "file_size": 1024,
            "file_content": "base64content",
        }

        # Act
        from main import app

        client = TestClient(app)
        response = client.post(
            f"/v1/submissions/{submission_id}/files",
            json=file_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
