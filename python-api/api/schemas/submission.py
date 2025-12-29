"""
Pydantic schemas for submission endpoints.

Defines request and response models for project submission functionality
including file uploads, submission status management, and metadata.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# Type for valid submission status
SubmissionStatus = Literal["DRAFT", "SUBMITTED", "SCORED"]


# File Metadata Schemas
class FileMetadata(BaseModel):
    """
    Metadata for a single uploaded file.

    Attributes:
        file_id: Unique identifier for the file in ZeroDB storage
        file_name: Original filename
        file_url: URL to access the file (presigned or public)
        file_type: MIME type of the file
        file_size: Size in bytes
        uploaded_at: Timestamp when file was uploaded
    """

    file_id: str = Field(..., description="ZeroDB file ID")
    file_name: str = Field(..., min_length=1, max_length=255, description="Original filename")
    file_url: str = Field(..., description="URL to access the file")
    file_type: str = Field(..., description="MIME type (e.g., 'application/pdf')")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    uploaded_at: datetime = Field(..., description="Upload timestamp")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """Ensure filename is not just whitespace."""
        if not v.strip():
            raise ValueError("File name cannot be empty or whitespace")
        return v.strip()

    class Config:
        from_attributes = True


# Submission Creation Schemas
class SubmissionCreateRequest(BaseModel):
    """
    Request schema for creating a new submission.

    Attributes:
        team_id: UUID of the team submitting the project
        hackathon_id: UUID of the hackathon
        project_name: Name of the project
        description: Project description
        repository_url: Optional Git repository URL
        demo_url: Optional live demo URL
        video_url: Optional demo video URL
        files: Optional list of file metadata for uploaded files
    """

    team_id: UUID = Field(..., description="Team ID")
    hackathon_id: UUID = Field(..., description="Hackathon ID")
    project_name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str = Field(..., min_length=10, max_length=5000, description="Project description")
    repository_url: Optional[str] = Field(None, max_length=500, description="Git repository URL")
    demo_url: Optional[str] = Field(None, max_length=500, description="Live demo URL")
    video_url: Optional[str] = Field(None, max_length=500, description="Demo video URL")
    files: Optional[List[FileMetadata]] = Field(default_factory=list, description="Uploaded files")

    @field_validator("project_name", "description")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensure fields are not just whitespace."""
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()

    @field_validator("repository_url", "demo_url", "video_url")
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v and not v.strip():
            return None
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.strip() if v else None


# Submission Update Schemas
class SubmissionUpdateRequest(BaseModel):
    """
    Request schema for updating an existing submission.

    All fields are optional to allow partial updates.

    Attributes:
        project_name: Optional new project name
        description: Optional new description
        repository_url: Optional new repository URL
        demo_url: Optional new demo URL
        video_url: Optional new video URL
        status: Optional new status (DRAFT, SUBMITTED, SCORED)
        files: Optional updated list of file metadata
    """

    project_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=10, max_length=5000)
    repository_url: Optional[str] = Field(None, max_length=500)
    demo_url: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    status: Optional[SubmissionStatus] = None
    files: Optional[List[FileMetadata]] = None

    @field_validator("project_name", "description")
    @classmethod
    def validate_non_empty(cls, v: Optional[str]) -> Optional[str]:
        """Ensure fields are not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip() if v else None

    @field_validator("repository_url", "demo_url", "video_url")
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v is not None and not v.strip():
            return None
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.strip() if v else None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[SubmissionStatus]) -> Optional[SubmissionStatus]:
        """Validate status is a valid value."""
        if v is not None and v not in ["DRAFT", "SUBMITTED", "SCORED"]:
            raise ValueError("Status must be 'DRAFT', 'SUBMITTED', or 'SCORED'")
        return v


# Submission Response Schemas
class SubmissionResponse(BaseModel):
    """
    Response schema for a single submission.

    Attributes:
        submission_id: Unique submission identifier
        team_id: Team UUID
        hackathon_id: Hackathon UUID
        project_name: Project name
        description: Project description
        repository_url: Git repository URL
        demo_url: Live demo URL
        video_url: Demo video URL
        status: Submission status (DRAFT, SUBMITTED, SCORED)
        files: List of uploaded file metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
        submitted_at: Submission timestamp (when status changed to SUBMITTED)
    """

    submission_id: UUID
    team_id: UUID
    hackathon_id: UUID
    project_name: str
    description: str
    repository_url: Optional[str]
    demo_url: Optional[str]
    video_url: Optional[str]
    status: SubmissionStatus
    files: List[FileMetadata]
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime]

    class Config:
        from_attributes = True


class SubmissionListResponse(BaseModel):
    """
    Response schema for listing submissions.

    Attributes:
        submissions: List of submissions
        total: Total number of submissions
        skip: Number of submissions skipped (pagination)
        limit: Maximum number of submissions returned
    """

    submissions: List[SubmissionResponse]
    total: int = Field(..., ge=0, description="Total submissions count")
    skip: int = Field(default=0, ge=0, description="Pagination offset")
    limit: int = Field(default=100, ge=1, le=1000, description="Pagination limit")

    class Config:
        from_attributes = True


# File Upload Schemas
class FileUploadRequest(BaseModel):
    """
    Request schema for uploading a file to a submission.

    Attributes:
        file_name: Name of the file
        file_type: MIME type of the file
        file_size: Size in bytes
        file_content: Base64-encoded file content
    """

    file_name: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., ge=1, le=100_000_000, description="Max 100MB")
    file_content: str = Field(..., description="Base64-encoded file content")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """Ensure filename is not just whitespace."""
        if not v.strip():
            raise ValueError("File name cannot be empty or whitespace")
        return v.strip()

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        """Validate MIME type format."""
        if "/" not in v:
            raise ValueError("Invalid MIME type format (expected 'type/subtype')")
        return v


class FileUploadResponse(BaseModel):
    """
    Response schema for file upload.

    Attributes:
        file_id: ZeroDB file ID
        file_name: Name of the uploaded file
        file_url: URL to access the file
        file_type: MIME type
        file_size: Size in bytes
        uploaded_at: Upload timestamp
    """

    file_id: str
    file_name: str
    file_url: str
    file_type: str
    file_size: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


# Error Response Schema
class ErrorResponse(BaseModel):
    """
    Standard error response schema.

    Attributes:
        error: Error message
        detail: Additional error details
        status_code: HTTP status code
    """

    error: str
    detail: Optional[str] = None
    status_code: int
