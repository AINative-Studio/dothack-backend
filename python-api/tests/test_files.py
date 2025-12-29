"""
Tests for file upload and management functionality.

Tests cover:
- File validation (size, type, extension)
- Team logo uploads
- Submission file uploads
- Presigned URL generation
- File listing and deletion
- Error handling and edge cases
"""

import base64
import io
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile
from integrations.zerodb.exceptions import ZeroDBError, ZeroDBNotFound
from services.file_service import (
    MAX_FILE_SIZE,
    delete_file,
    generate_download_url,
    get_content_type,
    get_file_category,
    get_file_metadata,
    list_team_files,
    upload_submission_file,
    upload_team_logo,
    validate_file,
)


class TestFileValidation:
    """Test file validation logic."""

    def test_validate_file_success_image(self):
        """Test successful validation for image file."""
        is_valid, error = validate_file("logo.png", 5_000_000, ["image"])
        assert is_valid is True
        assert error is None

    def test_validate_file_success_pdf(self):
        """Test successful validation for PDF file."""
        is_valid, error = validate_file("document.pdf", 8_000_000, ["pdf"])
        assert is_valid is True
        assert error is None

    def test_validate_file_success_video(self):
        """Test successful validation for video file."""
        is_valid, error = validate_file("demo.mp4", 9_000_000, ["video"])
        assert is_valid is True
        assert error is None

    def test_validate_file_success_all_types(self):
        """Test validation when all types are allowed."""
        is_valid, error = validate_file("file.jpg", 5_000_000, None)
        assert is_valid is True
        assert error is None

    def test_validate_file_size_too_large(self):
        """Test validation fails when file exceeds max size."""
        is_valid, error = validate_file("huge.png", MAX_FILE_SIZE + 1, ["image"])
        assert is_valid is False
        assert "exceeds maximum allowed size" in error

    def test_validate_file_size_zero(self):
        """Test validation fails for zero-byte file."""
        is_valid, error = validate_file("empty.png", 0, ["image"])
        assert is_valid is False
        assert "must be greater than 0" in error

    def test_validate_file_no_extension(self):
        """Test validation fails for file without extension."""
        is_valid, error = validate_file("noext", 5_000_000, ["image"])
        assert is_valid is False
        assert "must have an extension" in error

    def test_validate_file_wrong_type(self):
        """Test validation fails for wrong file type."""
        is_valid, error = validate_file("document.pdf", 5_000_000, ["image"])
        assert is_valid is False
        assert "not allowed" in error

    def test_validate_file_unsupported_extension(self):
        """Test validation fails for unsupported extension."""
        is_valid, error = validate_file("file.exe", 5_000_000, ["image"])
        assert is_valid is False
        assert "not allowed" in error


class TestFileUtilities:
    """Test file utility functions."""

    def test_get_content_type_png(self):
        """Test MIME type detection for PNG."""
        content_type = get_content_type("logo.png")
        assert content_type == "image/png"

    def test_get_content_type_jpg(self):
        """Test MIME type detection for JPG."""
        content_type = get_content_type("photo.jpg")
        assert content_type == "image/jpeg"

    def test_get_content_type_pdf(self):
        """Test MIME type detection for PDF."""
        content_type = get_content_type("doc.pdf")
        assert content_type == "application/pdf"

    def test_get_content_type_mp4(self):
        """Test MIME type detection for MP4."""
        content_type = get_content_type("video.mp4")
        assert content_type == "video/mp4"

    def test_get_content_type_unknown(self):
        """Test MIME type fallback for unknown extension."""
        content_type = get_content_type("file.unknownext")
        assert content_type == "application/octet-stream"

    def test_get_file_category_image(self):
        """Test category detection for image files."""
        assert get_file_category("logo.png") == "image"
        assert get_file_category("photo.jpg") == "image"
        assert get_file_category("img.gif") == "image"

    def test_get_file_category_pdf(self):
        """Test category detection for PDF files."""
        assert get_file_category("doc.pdf") == "pdf"

    def test_get_file_category_video(self):
        """Test category detection for video files."""
        assert get_file_category("demo.mp4") == "video"
        assert get_file_category("clip.mov") == "video"

    def test_get_file_category_unknown(self):
        """Test category detection for unknown files."""
        assert get_file_category("file.xyz") is None


class TestUploadTeamLogo:
    """Test team logo upload service function."""

    @pytest.mark.asyncio
    async def test_upload_team_logo_success(self):
        """Test successful team logo upload."""
        # Mock ZeroDB client
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.upload_file = AsyncMock(
            return_value={
                "file_id": "file_abc123",
                "file_name": "logo.png",
                "content_type": "image/png",
                "size": 5000,
                "folder": "teams/team-123/logos",
                "metadata": {"team_id": "team-123", "file_type": "team_logo"},
                "created_at": "2024-12-28T10:00:00Z",
            }
        )

        # Upload logo
        file_content = b"fake image content"
        result = await upload_team_logo(mock_client, "team-123", file_content, "logo.png")

        # Verify result
        assert result["file_id"] == "file_abc123"
        assert result["file_name"] == "logo.png"
        assert result["metadata"]["team_id"] == "team-123"

        # Verify upload was called correctly
        mock_client.files.upload_file.assert_called_once()
        call_args = mock_client.files.upload_file.call_args
        assert call_args.kwargs["file_name"] == "logo.png"
        assert call_args.kwargs["content_type"] == "image/png"
        assert call_args.kwargs["folder"] == "teams/team-123/logos"

    @pytest.mark.asyncio
    async def test_upload_team_logo_validation_failure(self):
        """Test team logo upload with invalid file."""
        mock_client = MagicMock()

        # Try to upload PDF (not allowed for logo)
        file_content = b"fake pdf content"
        with pytest.raises(ValueError) as exc_info:
            await upload_team_logo(mock_client, "team-123", file_content, "document.pdf")

        assert "not allowed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_team_logo_size_too_large(self):
        """Test team logo upload with file too large."""
        mock_client = MagicMock()

        # Create file larger than max size
        file_content = b"x" * (MAX_FILE_SIZE + 1)
        with pytest.raises(ValueError) as exc_info:
            await upload_team_logo(mock_client, "team-123", file_content, "huge.png")

        assert "exceeds maximum allowed size" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_team_logo_zerodb_error(self):
        """Test team logo upload with ZeroDB error."""
        # Mock ZeroDB client that raises error
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.upload_file = AsyncMock(side_effect=ZeroDBError("Upload failed"))

        file_content = b"fake image content"
        with pytest.raises(ZeroDBError):
            await upload_team_logo(mock_client, "team-123", file_content, "logo.png")


class TestUploadSubmissionFile:
    """Test submission file upload service function."""

    @pytest.mark.asyncio
    async def test_upload_submission_file_image(self):
        """Test successful submission image upload."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.upload_file = AsyncMock(
            return_value={
                "file_id": "file_xyz789",
                "file_name": "screenshot.png",
                "content_type": "image/png",
                "size": 3000,
            }
        )

        file_content = b"fake image"
        result = await upload_submission_file(
            mock_client, "sub-123", file_content, "screenshot.png", "image"
        )

        assert result["file_id"] == "file_xyz789"
        mock_client.files.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_submission_file_video(self):
        """Test successful submission video upload."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.upload_file = AsyncMock(
            return_value={
                "file_id": "file_vid456",
                "file_name": "demo.mp4",
                "content_type": "video/mp4",
                "size": 8000000,
            }
        )

        file_content = b"fake video content"
        result = await upload_submission_file(
            mock_client, "sub-456", file_content, "demo.mp4", "video"
        )

        assert result["file_id"] == "file_vid456"

    @pytest.mark.asyncio
    async def test_upload_submission_file_invalid_type(self):
        """Test submission file upload with invalid file_type."""
        mock_client = MagicMock()

        file_content = b"content"
        with pytest.raises(ValueError) as exc_info:
            await upload_submission_file(mock_client, "sub-123", file_content, "file.txt", "invalid")

        assert "Invalid file_type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_submission_file_wrong_extension(self):
        """Test submission file upload with wrong extension for type."""
        mock_client = MagicMock()

        # Try to upload PDF with file_type="video"
        file_content = b"pdf content"
        with pytest.raises(ValueError) as exc_info:
            await upload_submission_file(mock_client, "sub-123", file_content, "doc.pdf", "video")

        assert "not allowed" in str(exc_info.value)


class TestGenerateDownloadURL:
    """Test presigned URL generation."""

    @pytest.mark.asyncio
    async def test_generate_download_url_success(self):
        """Test successful presigned URL generation."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.generate_presigned_url = AsyncMock(
            return_value={
                "url": "https://storage.example.com/file_abc?signature=xyz",
                "expires_at": "2024-12-28T11:00:00Z",
                "file_id": "file_abc",
            }
        )

        result = await generate_download_url(mock_client, "file_abc", 1800)

        assert result["url"].startswith("https://")
        assert result["file_id"] == "file_abc"
        mock_client.files.generate_presigned_url.assert_called_once_with(
            file_id="file_abc", expiration_seconds=1800
        )

    @pytest.mark.asyncio
    async def test_generate_download_url_not_found(self):
        """Test presigned URL generation for non-existent file."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.generate_presigned_url = AsyncMock(side_effect=ZeroDBNotFound("Not found"))

        with pytest.raises(ZeroDBNotFound):
            await generate_download_url(mock_client, "nonexistent", 3600)


class TestListTeamFiles:
    """Test team file listing."""

    @pytest.mark.asyncio
    async def test_list_team_files_success(self):
        """Test successful file listing."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.list_files = AsyncMock(
            return_value={
                "files": [
                    {"file_id": "file_1", "file_name": "logo.png"},
                    {"file_id": "file_2", "file_name": "banner.jpg"},
                ],
                "total": 2,
                "limit": 100,
                "offset": 0,
            }
        )

        result = await list_team_files(mock_client, "team-123", 100, 0)

        assert result["total"] == 2
        assert len(result["files"]) == 2
        mock_client.files.list_files.assert_called_once_with(
            folder="teams/team-123", limit=100, offset=0
        )

    @pytest.mark.asyncio
    async def test_list_team_files_empty(self):
        """Test file listing with no files."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.list_files = AsyncMock(
            return_value={"files": [], "total": 0, "limit": 100, "offset": 0}
        )

        result = await list_team_files(mock_client, "team-456", 100, 0)

        assert result["total"] == 0
        assert len(result["files"]) == 0


class TestDeleteFile:
    """Test file deletion."""

    @pytest.mark.asyncio
    async def test_delete_file_success(self):
        """Test successful file deletion."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.delete_file = AsyncMock(
            return_value={
                "success": True,
                "file_id": "file_abc",
                "message": "File deleted successfully",
            }
        )

        result = await delete_file(mock_client, "file_abc")

        assert result["success"] is True
        assert result["file_id"] == "file_abc"
        mock_client.files.delete_file.assert_called_once_with(file_id="file_abc")

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self):
        """Test file deletion for non-existent file."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.delete_file = AsyncMock(side_effect=ZeroDBNotFound("Not found"))

        with pytest.raises(ZeroDBNotFound):
            await delete_file(mock_client, "nonexistent")


class TestGetFileMetadata:
    """Test file metadata retrieval."""

    @pytest.mark.asyncio
    async def test_get_file_metadata_success(self):
        """Test successful metadata retrieval."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.get_file_metadata = AsyncMock(
            return_value={
                "file_id": "file_abc",
                "file_name": "logo.png",
                "content_type": "image/png",
                "size": 5000,
                "folder": "teams/team-123/logos",
                "metadata": {"team_id": "team-123"},
                "created_at": "2024-12-28T10:00:00Z",
            }
        )

        result = await get_file_metadata(mock_client, "file_abc")

        assert result["file_id"] == "file_abc"
        assert result["size"] == 5000
        mock_client.files.get_file_metadata.assert_called_once_with(file_id="file_abc")

    @pytest.mark.asyncio
    async def test_get_file_metadata_not_found(self):
        """Test metadata retrieval for non-existent file."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.get_file_metadata = AsyncMock(side_effect=ZeroDBNotFound("Not found"))

        with pytest.raises(ZeroDBNotFound):
            await get_file_metadata(mock_client, "nonexistent")


# Edge case and integration tests
class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_validate_file_multiple_dots_in_filename(self):
        """Test validation for filename with multiple dots."""
        is_valid, error = validate_file("my.logo.final.png", 5000, ["image"])
        assert is_valid is True
        assert error is None

    def test_validate_file_uppercase_extension(self):
        """Test validation for uppercase extension."""
        is_valid, error = validate_file("LOGO.PNG", 5000, ["image"])
        assert is_valid is True  # Extensions are lowercased

    def test_get_content_type_case_insensitive(self):
        """Test MIME type detection is case-insensitive."""
        assert get_content_type("FILE.PNG") == "image/png"
        assert get_content_type("file.PNG") == "image/png"

    @pytest.mark.asyncio
    async def test_upload_team_logo_exact_max_size(self):
        """Test upload at exactly max file size (boundary test)."""
        mock_client = MagicMock()
        mock_client.files = MagicMock()
        mock_client.files.upload_file = AsyncMock(return_value={"file_id": "test"})

        # Exactly at max size should succeed
        file_content = b"x" * MAX_FILE_SIZE
        result = await upload_team_logo(mock_client, "team-123", file_content, "logo.png")

        assert result["file_id"] == "test"
