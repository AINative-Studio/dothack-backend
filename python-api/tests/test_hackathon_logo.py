"""
Tests for Hackathon Logo Upload/Delete

Comprehensive test suite for logo upload and deletion operations.
Tests authorization, validation, file handling, and error cases.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.hackathon_service import (
    delete_hackathon_logo,
    upload_hackathon_logo,
)


# Fixtures
@pytest.fixture
def mock_zerodb_client():
    """Create a mock ZeroDB client with files API."""
    client = MagicMock()
    client.tables = MagicMock()
    client.files = MagicMock()
    client.project_id = "test-project-123"
    return client


@pytest.fixture
def sample_hackathon_row():
    """Sample hackathon row from ZeroDB."""
    hackathon_id = str(uuid.uuid4())
    organizer_id = str(uuid.uuid4())
    return {
        "hackathon_id": hackathon_id,
        "name": "AI Hackathon 2024",
        "description": "Build AI apps",
        "organizer_id": organizer_id,
        "start_date": "2024-03-01T09:00:00Z",
        "end_date": "2024-03-03T18:00:00Z",
        "location": "virtual",
        "logo_url": None,
        "is_online": True,
        "participant_count": 0,
        "status": "draft",
        "is_deleted": False,
    }


@pytest.fixture
def sample_logo_image():
    """Sample PNG image bytes (minimal valid PNG header)."""
    # PNG signature + IHDR chunk
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        b'\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00'
        b'\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


# Tests for upload_hackathon_logo()
class TestUploadHackathonLogo:
    """Tests for logo upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_logo_success(
        self, mock_zerodb_client, sample_hackathon_row, sample_logo_image
    ):
        """Test successful logo upload."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # Mock authorization check
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],  # Auth
                [sample_hackathon_row],  # Get hackathon
            ]
        )

        # Mock file upload
        file_id = str(uuid.uuid4())
        mock_zerodb_client.files.upload_file = AsyncMock(
            return_value={"file_id": file_id, "file_name": "logo.png"}
        )

        # Mock presigned URL generation
        logo_url = f"https://storage.example.com/files/{file_id}"
        mock_zerodb_client.files.generate_presigned_url = AsyncMock(
            return_value={"url": logo_url, "expires_at": "2024-03-10T00:00:00Z"}
        )

        # Mock hackathon update
        mock_zerodb_client.tables.update_rows = AsyncMock(return_value={"success": True})

        # Act
        result = await upload_hackathon_logo(
            zerodb_client=mock_zerodb_client,
            hackathon_id=hackathon_id,
            user_id=organizer_id,
            file_content=sample_logo_image,
            file_name="logo.png",
            content_type="image/png",
        )

        # Assert
        assert result["success"] is True
        assert result["hackathon_id"] == hackathon_id
        assert result["logo_url"] == logo_url
        assert "uploaded successfully" in result["message"].lower()

        # Verify file upload was called correctly
        mock_zerodb_client.files.upload_file.assert_called_once()
        call_kwargs = mock_zerodb_client.files.upload_file.call_args.kwargs
        assert call_kwargs["file_name"] == "logo.png"
        assert call_kwargs["content_type"] == "image/png"
        assert call_kwargs["folder"] == f"hackathons/{hackathon_id}/logos"

    @pytest.mark.asyncio
    async def test_upload_logo_invalid_format(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test upload fails with invalid image format."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_hackathon_logo(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=organizer_id,
                file_content=b"fake image data",
                file_name="logo.webp",
                content_type="image/webp",  # Not allowed
            )

        assert exc_info.value.status_code == 400
        assert "invalid image format" in str(exc_info.value.detail).lower()
        assert "webp" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_upload_logo_file_too_large(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test upload fails when file exceeds 5MB limit."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        # Create file larger than 5MB
        large_file = b"x" * (6 * 1024 * 1024)  # 6MB

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_hackathon_logo(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=organizer_id,
                file_content=large_file,
                file_name="logo.png",
                content_type="image/png",
            )

        assert exc_info.value.status_code == 400
        assert "file too large" in str(exc_info.value.detail).lower()
        assert "5mb" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_upload_logo_unauthorized(
        self, mock_zerodb_client, sample_hackathon_row, sample_logo_image
    ):
        """Test upload fails when user is not ORGANIZER."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        unauthorized_user_id = str(uuid.uuid4())

        # Mock authorization failure
        mock_zerodb_client.tables.query_rows = AsyncMock(
            return_value=[]  # No participant record - unauthorized
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_hackathon_logo(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=unauthorized_user_id,
                file_content=sample_logo_image,
                file_name="logo.png",
                content_type="image/png",
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_upload_logo_hackathon_not_found(
        self, mock_zerodb_client, sample_logo_image
    ):
        """Test upload fails when hackathon doesn't exist."""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Mock authorization success but hackathon not found
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": user_id, "role": "organizer", "hackathon_id": hackathon_id}],  # Auth
                [],  # Hackathon not found
            ]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_hackathon_logo(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=user_id,
                file_content=sample_logo_image,
                file_name="logo.png",
                content_type="image/png",
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_logo_database_timeout(
        self, mock_zerodb_client, sample_hackathon_row, sample_logo_image
    ):
        """Test upload handles database timeout."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        # Mock file upload timeout
        mock_zerodb_client.files.upload_file = AsyncMock(
            side_effect=ZeroDBTimeoutError("Upload timeout")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_hackathon_logo(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=organizer_id,
                file_content=sample_logo_image,
                file_name="logo.png",
                content_type="image/png",
            )

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_upload_logo_accepts_jpg(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test upload accepts JPEG format."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # JPEG header
        jpg_image = b'\xff\xd8\xff\xe0\x00\x10JFIF'

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        file_id = str(uuid.uuid4())
        mock_zerodb_client.files.upload_file = AsyncMock(return_value={"file_id": file_id})
        mock_zerodb_client.files.generate_presigned_url = AsyncMock(
            return_value={"url": f"https://example.com/{file_id}"}
        )
        mock_zerodb_client.tables.update_rows = AsyncMock(return_value={"success": True})

        # Act
        result = await upload_hackathon_logo(
            zerodb_client=mock_zerodb_client,
            hackathon_id=hackathon_id,
            user_id=organizer_id,
            file_content=jpg_image,
            file_name="logo.jpg",
            content_type="image/jpeg",
        )

        # Assert
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_upload_logo_accepts_svg(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test upload accepts SVG format."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        svg_image = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        file_id = str(uuid.uuid4())
        mock_zerodb_client.files.upload_file = AsyncMock(return_value={"file_id": file_id})
        mock_zerodb_client.files.generate_presigned_url = AsyncMock(
            return_value={"url": f"https://example.com/{file_id}"}
        )
        mock_zerodb_client.tables.update_rows = AsyncMock(return_value={"success": True})

        # Act
        result = await upload_hackathon_logo(
            zerodb_client=mock_zerodb_client,
            hackathon_id=hackathon_id,
            user_id=organizer_id,
            file_content=svg_image,
            file_name="logo.svg",
            content_type="image/svg+xml",
        )

        # Assert
        assert result["success"] is True


# Tests for delete_hackathon_logo()
class TestDeleteHackathonLogo:
    """Tests for logo deletion functionality."""

    @pytest.mark.asyncio
    async def test_delete_logo_success(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test successful logo deletion."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]
        sample_hackathon_row["logo_url"] = "https://example.com/logo.png"

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        # Mock update operation
        mock_zerodb_client.tables.update_rows = AsyncMock(return_value={"success": True})

        # Act
        result = await delete_hackathon_logo(
            zerodb_client=mock_zerodb_client,
            hackathon_id=hackathon_id,
            user_id=organizer_id,
        )

        # Assert
        assert result["success"] is True
        assert result["hackathon_id"] == hackathon_id
        assert "removed successfully" in result["message"].lower()

        # Verify update was called to clear logo_url
        mock_zerodb_client.tables.update_rows.assert_called_once()
        call_args = mock_zerodb_client.tables.update_rows.call_args
        assert call_args[1]["filter"]["hackathon_id"] == hackathon_id
        assert call_args[1]["update"]["$set"]["logo_url"] is None

    @pytest.mark.asyncio
    async def test_delete_logo_unauthorized(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test delete fails when user is not ORGANIZER."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        unauthorized_user_id = str(uuid.uuid4())

        # Mock authorization failure
        mock_zerodb_client.tables.query_rows = AsyncMock(
            return_value=[]  # No participant record
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_hackathon_logo(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=unauthorized_user_id,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_logo_hackathon_not_found(self, mock_zerodb_client):
        """Test delete fails when hackathon doesn't exist."""
        # Arrange
        hackathon_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Mock authorization success but hackathon not found
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": user_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [],  # Hackathon not found
            ]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_hackathon_logo(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=user_id,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_logo_database_error(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test delete handles database errors."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        # Mock update failure
        mock_zerodb_client.tables.update_rows = AsyncMock(
            side_effect=ZeroDBError("Database error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_hackathon_logo(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=organizer_id,
            )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_delete_logo_timeout(
        self, mock_zerodb_client, sample_hackathon_row
    ):
        """Test delete handles timeout."""
        # Arrange
        hackathon_id = sample_hackathon_row["hackathon_id"]
        organizer_id = sample_hackathon_row["organizer_id"]

        # Mock authorization and get hackathon
        mock_zerodb_client.tables.query_rows = AsyncMock(
            side_effect=[
                [{"user_id": organizer_id, "role": "organizer", "hackathon_id": hackathon_id}],
                [sample_hackathon_row],
            ]
        )

        # Mock timeout
        mock_zerodb_client.tables.update_rows = AsyncMock(
            side_effect=ZeroDBTimeoutError("Timeout")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_hackathon_logo(
                zerodb_client=mock_zerodb_client,
                hackathon_id=hackathon_id,
                user_id=organizer_id,
            )

        assert exc_info.value.status_code == 504
