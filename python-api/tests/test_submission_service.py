"""
Tests for Submission Service

Comprehensive tests for submission CRUD operations, file uploads,
and submission status management using ZeroDB.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.submission_service import (
    create_submission,
    delete_submission,
    get_submission,
    list_submissions,
    update_submission,
    upload_file_to_submission,
)


class TestCreateSubmission:
    """Test create_submission() function"""

    @pytest.mark.asyncio
    async def test_create_submission_success(self):
        """Should create submission in DRAFT status"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        team_id = str(uuid.uuid4())
        hackathon_id = str(uuid.uuid4())

        # Mock team exists
        mock_client.tables.query_rows.side_effect = [
            [{"team_id": team_id, "name": "Team Alpha"}],  # Team check
            [  # Return created submission
                {
                    "submission_id": submission_id,
                    "team_id": team_id,
                    "hackathon_id": hackathon_id,
                    "project_name": "AI Assistant",
                    "description": "An intelligent coding assistant",
                    "status": "DRAFT",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ],
        ]

        mock_client.tables.insert_rows.return_value = {"inserted_ids": [submission_id]}

        # Act
        result = await create_submission(
            zerodb_client=mock_client,
            team_id=team_id,
            hackathon_id=hackathon_id,
            project_name="AI Assistant",
            description="An intelligent coding assistant",
        )

        # Assert
        assert result["submission_id"] == submission_id
        assert result["status"] == "DRAFT"
        assert result["project_name"] == "AI Assistant"
        assert mock_client.tables.insert_rows.call_count == 1

    @pytest.mark.asyncio
    async def test_create_submission_with_optional_fields(self):
        """Should create submission with all optional fields"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())
        files = [
            {
                "file_id": "file-1",
                "file_name": "demo.pdf",
                "file_url": "https://example.com/demo.pdf",
                "file_type": "application/pdf",
                "file_size": 1024,
                "uploaded_at": datetime.utcnow().isoformat(),
            }
        ]

        mock_client.tables.query_rows.side_effect = [
            [{"team_id": str(uuid.uuid4())}],  # Team exists
            [
                {
                    "submission_id": submission_id,
                    "repository_url": "https://github.com/test/repo",
                    "demo_url": "https://demo.example.com",
                    "video_url": "https://youtube.com/watch?v=123",
                    "files": files,
                }
            ],
        ]

        mock_client.tables.insert_rows.return_value = {"inserted_ids": [submission_id]}

        # Act
        result = await create_submission(
            zerodb_client=mock_client,
            team_id=str(uuid.uuid4()),
            hackathon_id=str(uuid.uuid4()),
            project_name="Full Featured Project",
            description="A complete project with all fields",
            repository_url="https://github.com/test/repo",
            demo_url="https://demo.example.com",
            video_url="https://youtube.com/watch?v=123",
            files=files,
        )

        # Assert
        assert result["repository_url"] == "https://github.com/test/repo"
        assert result["demo_url"] == "https://demo.example.com"
        assert result["video_url"] == "https://youtube.com/watch?v=123"
        assert len(result["files"]) == 1

    @pytest.mark.asyncio
    async def test_create_submission_validates_project_name_not_empty(self):
        """Should raise ValueError for empty project name"""
        # Arrange
        mock_client = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await create_submission(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                hackathon_id=str(uuid.uuid4()),
                project_name="",
                description="Valid description here",
            )
        assert "Project name cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_submission_validates_description_empty(self):
        """Should raise ValueError for empty description"""
        # Arrange
        mock_client = AsyncMock()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await create_submission(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                hackathon_id=str(uuid.uuid4()),
                project_name="Project",
                description="",
            )
        assert "Description cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_submission_team_not_found(self):
        """Should raise 404 if team doesn't exist"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []  # Team not found

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_submission(
                zerodb_client=mock_client,
                team_id=str(uuid.uuid4()),
                hackathon_id=str(uuid.uuid4()),
                project_name="Project",
                description="Valid description here",
            )
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail


class TestGetSubmission:
    """Test get_submission() function"""

    @pytest.mark.asyncio
    async def test_get_submission_success(self):
        """Should retrieve submission by ID"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {
                "submission_id": submission_id,
                "project_name": "Test Project",
                "status": "DRAFT",
                "files": [],
            }
        ]

        # Act
        result = await get_submission(
            zerodb_client=mock_client,
            submission_id=submission_id,
            requester_id=str(uuid.uuid4()),
        )

        # Assert
        assert result["submission_id"] == submission_id
        assert result["project_name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_get_submission_not_found(self):
        """Should raise 404 if submission doesn't exist"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_submission(
                zerodb_client=mock_client,
                submission_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4()),
            )
        assert exc_info.value.status_code == 404


class TestListSubmissions:
    """Test list_submissions() function"""

    @pytest.mark.asyncio
    async def test_list_submissions_all(self):
        """Should list all submissions for hackathon"""
        # Arrange
        mock_client = AsyncMock()
        hackathon_id = str(uuid.uuid4())

        submissions = [
            {"submission_id": str(uuid.uuid4()), "status": "DRAFT"},
            {"submission_id": str(uuid.uuid4()), "status": "SUBMITTED"},
            {"submission_id": str(uuid.uuid4()), "status": "DRAFT"},
        ]

        mock_client.tables.query_rows.return_value = submissions

        # Act
        result = await list_submissions(
            zerodb_client=mock_client,
            requester_id=str(uuid.uuid4()),
            hackathon_id=hackathon_id,
            skip=0,
            limit=100,
        )

        # Assert
        assert len(result) == 3
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_submissions_filter_by_status(self):
        """Should filter submissions by status"""
        # Arrange
        mock_client = AsyncMock()
        submitted = [{"submission_id": str(uuid.uuid4()), "status": "SUBMITTED"}]

        mock_client.tables.query_rows.return_value = submitted

        # Act
        result = await list_submissions(
            zerodb_client=mock_client,
            requester_id=str(uuid.uuid4()),
            hackathon_id=str(uuid.uuid4()),
            status="SUBMITTED",
        )

        # Assert
        assert len(result) == 1
        assert result[0]["status"] == "SUBMITTED"

    @pytest.mark.asyncio
    async def test_list_submissions_filter_by_team(self):
        """Should filter submissions by team"""
        # Arrange
        mock_client = AsyncMock()
        team_id = str(uuid.uuid4())
        team_submissions = [{"team_id": team_id, "status": "DRAFT"}]

        mock_client.tables.query_rows.return_value = team_submissions

        # Act
        result = await list_submissions(
            zerodb_client=mock_client,
            requester_id=str(uuid.uuid4()),
            hackathon_id=str(uuid.uuid4()),
            team_id=team_id,
        )

        # Assert
        assert len(result) == 1
        assert result[0]["team_id"] == team_id


class TestUpdateSubmission:
    """Test update_submission() function"""

    @pytest.mark.asyncio
    async def test_update_submission_success(self):
        """Should update submission fields"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())

        mock_client.tables.query_rows.side_effect = [
            [{"submission_id": submission_id, "status": "DRAFT"}],  # Initial check
            [{  # After update
                "submission_id": submission_id,
                "project_name": "Updated Project",
                "description": "Updated description here",
                "status": "DRAFT",
            }]
        ]

        mock_client.tables.update_rows.return_value = {"success": True}

        # Act
        result = await update_submission(
            zerodb_client=mock_client,
            submission_id=submission_id,
            requester_id=str(uuid.uuid4()),
            project_name="Updated Project",
            description="Updated description here",
        )

        # Assert
        assert result["project_name"] == "Updated Project"
        assert mock_client.tables.update_rows.call_count == 1

    @pytest.mark.asyncio
    async def test_update_submission_status_to_submitted(self):
        """Should update status and set submitted_at"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())

        mock_client.tables.query_rows.side_effect = [
            [{"submission_id": submission_id, "status": "DRAFT"}],  # Initial check
            [{  # After update
                "submission_id": submission_id,
                "status": "SUBMITTED",
                "submitted_at": datetime.utcnow().isoformat(),
            }]
        ]

        mock_client.tables.update_rows.return_value = {"success": True}

        # Act
        result = await update_submission(
            zerodb_client=mock_client,
            submission_id=submission_id,
            status="SUBMITTED",
            requester_id=str(uuid.uuid4()),
        )

        # Assert
        assert result["status"] == "SUBMITTED"
        assert "submitted_at" in result

    @pytest.mark.asyncio
    async def test_update_submission_validates_status(self):
        """Should raise ValueError for invalid status"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"submission_id": str(uuid.uuid4()), "status": "DRAFT"}
        ]

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await update_submission(
                zerodb_client=mock_client,
                submission_id=str(uuid.uuid4()),
                status="INVALID_STATUS",
                requester_id=str(uuid.uuid4()),
            )
        assert "Invalid status" in str(exc_info.value)


class TestDeleteSubmission:
    """Test delete_submission() function"""

    @pytest.mark.asyncio
    async def test_delete_submission_success(self):
        """Should delete submission that is not SCORED"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {"submission_id": submission_id, "status": "DRAFT"}
        ]

        mock_client.tables.delete_rows.return_value = {"success": True}

        # Act
        result = await delete_submission(
            zerodb_client=mock_client,
            submission_id=submission_id,
            requester_id=str(uuid.uuid4()),
        )

        # Assert
        assert result["success"] is True
        mock_client.tables.delete_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_submission_prevents_deleting_scored(self):
        """Should raise 400 when trying to delete SCORED submission"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = [
            {"submission_id": str(uuid.uuid4()), "status": "SCORED"}
        ]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_submission(
                zerodb_client=mock_client,
                submission_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4()),
            )
        assert exc_info.value.status_code == 400
        assert "scored" in exc_info.value.detail.lower()


class TestUploadFile:
    """Test upload_file_to_submission() function"""

    @pytest.mark.asyncio
    async def test_upload_file_success(self):
        """Should upload file and update submission"""
        # Arrange
        mock_client = AsyncMock()
        submission_id = str(uuid.uuid4())

        mock_client.tables.query_rows.return_value = [
            {"submission_id": submission_id, "status": "DRAFT", "files": []}
        ]

        # Mock file upload
        mock_client.files.upload_file.return_value = {
            "file_id": "file-123",
            "file_url": "https://example.com/file-123"
        }

        mock_client.tables.update_rows.return_value = {"success": True}

        # Act
        result = await upload_file_to_submission(
            zerodb_client=mock_client,
            submission_id=submission_id,
            file_name="demo.pdf",
            file_type="application/pdf",
            file_size=1024,
            file_content="base64encodedcontent",
            requester_id=str(uuid.uuid4()),
        )

        # Assert
        assert result["file_name"] == "demo.pdf"
        assert result["file_type"] == "application/pdf"
        assert result["file_size"] == 1024
        assert "file_id" in result
        assert "file_url" in result
        mock_client.files.upload_file.assert_called_once()
        mock_client.tables.update_rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_file_submission_not_found(self):
        """Should raise 404 if submission doesn't exist"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.return_value = []

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_file_to_submission(
                zerodb_client=mock_client,
                submission_id=str(uuid.uuid4()),
                file_name="demo.pdf",
                file_type="application/pdf",
                file_size=1024,
                file_content="content",
                requester_id=str(uuid.uuid4()),
            )
        assert exc_info.value.status_code == 404


class TestErrorHandling:
    """Test error handling across all functions"""

    @pytest.mark.asyncio
    async def test_timeout_error_returns_504(self):
        """Should return 504 on timeout"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBTimeoutError("Timeout")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_submission(
                zerodb_client=mock_client,
                submission_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4()),
            )
        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_zerodb_error_returns_500(self):
        """Should return 500 on database error"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = ZeroDBError("DB Error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_submission(
                zerodb_client=mock_client,
                submission_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4()),
            )
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_500(self):
        """Should return 500 on unexpected error"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.tables.query_rows.side_effect = Exception("Unexpected")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_submission(
                zerodb_client=mock_client,
                submission_id=str(uuid.uuid4()),
                requester_id=str(uuid.uuid4()),
            )
        assert exc_info.value.status_code == 500
