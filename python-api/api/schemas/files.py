"""
Pydantic schemas for file upload and management endpoints.

Defines request and response models for file operations including
uploads, downloads, and metadata retrieval.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class FileType(str, Enum):
    """
    Allowed file type categories.

    Values:
        IMAGE: Image files (png, jpg, jpeg, gif)
        PDF: PDF documents
        VIDEO: Video files (mp4, mov)
    """

    IMAGE = "image"
    PDF = "pdf"
    VIDEO = "video"


class FileUploadResponse(BaseModel):
    """
    Response schema for file upload.

    Attributes:
        file_id: Unique file identifier
        file_name: Name of the uploaded file
        content_type: MIME type of the file
        size: File size in bytes
        folder: Virtual folder path
        metadata: Custom metadata dictionary
        created_at: Upload timestamp
        url: Optional public download URL
    """

    file_id: str = Field(..., description="Unique file identifier")
    file_name: str = Field(..., description="Name of the file")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    folder: Optional[str] = Field(None, description="Virtual folder path")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Custom metadata")
    created_at: str = Field(..., description="Upload timestamp (ISO 8601)")
    url: Optional[str] = Field(None, description="Public download URL (if available)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "file_id": "file_abc123xyz",
                "file_name": "team_logo.png",
                "content_type": "image/png",
                "size": 245678,
                "folder": "teams/team-123/logos",
                "metadata": {"team_id": "team-123", "file_type": "team_logo"},
                "created_at": "2024-12-28T10:30:00Z",
                "url": None,
            }
        }


class PresignedURLResponse(BaseModel):
    """
    Response schema for presigned URL generation.

    Attributes:
        url: Presigned download URL
        expires_at: URL expiration timestamp
        file_id: File identifier
    """

    url: str = Field(..., description="Presigned download URL")
    expires_at: str = Field(..., description="URL expiration timestamp (ISO 8601)")
    file_id: str = Field(..., description="File identifier")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "url": "https://storage.example.com/files/abc123?signature=xyz...",
                "expires_at": "2024-12-28T11:30:00Z",
                "file_id": "file_abc123xyz",
            }
        }


class FileMetadataResponse(BaseModel):
    """
    Response schema for file metadata.

    Attributes:
        file_id: Unique file identifier
        file_name: Name of the file
        content_type: MIME type
        size: File size in bytes
        folder: Virtual folder path
        metadata: Custom metadata
        created_at: Upload timestamp
    """

    file_id: str = Field(..., description="Unique file identifier")
    file_name: str = Field(..., description="Name of the file")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    folder: Optional[str] = Field(None, description="Virtual folder path")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Custom metadata")
    created_at: str = Field(..., description="Upload timestamp (ISO 8601)")

    class Config:
        from_attributes = True


class FileListItem(BaseModel):
    """
    Schema for individual file in list response.

    Attributes:
        file_id: Unique file identifier
        file_name: Name of the file
        content_type: MIME type
        size: File size in bytes
        folder: Virtual folder path
        created_at: Upload timestamp
    """

    file_id: str = Field(..., description="Unique file identifier")
    file_name: str = Field(..., description="Name of the file")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    folder: Optional[str] = Field(None, description="Virtual folder path")
    created_at: str = Field(..., description="Upload timestamp (ISO 8601)")


class FileListResponse(BaseModel):
    """
    Response schema for file listing.

    Attributes:
        files: List of file objects
        total: Total number of files matching filters
        limit: Items per page
        offset: Current offset
    """

    files: List[FileListItem] = Field(..., description="List of files")
    total: int = Field(..., description="Total files matching filters")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Current offset")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "files": [
                    {
                        "file_id": "file_abc123",
                        "file_name": "logo.png",
                        "content_type": "image/png",
                        "size": 245678,
                        "folder": "teams/team-123/logos",
                        "created_at": "2024-12-28T10:30:00Z",
                    }
                ],
                "total": 1,
                "limit": 100,
                "offset": 0,
            }
        }


class FileDeleteResponse(BaseModel):
    """
    Response schema for file deletion.

    Attributes:
        success: True if deleted successfully
        file_id: Deleted file identifier
        message: Confirmation message
    """

    success: bool = Field(..., description="Deletion success status")
    file_id: str = Field(..., description="Deleted file identifier")
    message: str = Field(..., description="Confirmation message")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "success": True,
                "file_id": "file_abc123xyz",
                "message": "File deleted successfully",
            }
        }


class SubmissionFileUploadRequest(BaseModel):
    """
    Request schema for submission file upload metadata.

    Attributes:
        file_type: Type of file being uploaded (image, pdf, video)
    """

    file_type: FileType = Field(..., description="Type of file (image, pdf, video)")

    class Config:
        json_schema_extra = {"example": {"file_type": "image"}}


class ErrorResponse(BaseModel):
    """
    Standard error response schema.

    Attributes:
        error: Error details object
    """

    error: Dict[str, Any] = Field(..., description="Error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "status_code": 400,
                    "message": "File size exceeds maximum allowed size of 10.0MB",
                    "path": "/api/v1/teams/team-123/logo",
                }
            }
        }
