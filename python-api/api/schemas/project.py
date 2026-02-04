"""
Pydantic schemas for hackathon project management endpoints.

Defines request and response models for project CRUD operations,
status management, and project listings.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


# Project Status Type
ProjectStatus = Literal["IDEA", "BUILDING", "SUBMITTED"]


class ProjectBase(BaseModel):
    """
    Base schema for project.

    Attributes:
        title: Project title (required)
        one_liner: Short project description
        description: Detailed project description
        repo_url: Repository URL
        demo_url: Demo/deployment URL
        video_url: Demo video URL
    """

    title: str = Field(..., min_length=1, max_length=200, description="Project title")
    one_liner: Optional[str] = Field(
        None, max_length=300, description="Short project description"
    )
    description: Optional[str] = Field(
        None, max_length=5000, description="Detailed project description"
    )
    repo_url: Optional[str] = Field(None, max_length=500, description="Repository URL")
    demo_url: Optional[str] = Field(
        None, max_length=500, description="Demo/deployment URL"
    )
    video_url: Optional[str] = Field(None, max_length=500, description="Demo video URL")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v.strip():
            raise ValueError("Project title cannot be empty or whitespace")
        return v.strip()

    @field_validator("repo_url", "demo_url", "video_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v is not None:
            v = v.strip()
            if v and not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("URL must start with http:// or https://")
        return v


class ProjectCreateRequest(ProjectBase):
    """
    Request schema for creating a new project.

    Attributes:
        hackathon_id: UUID of the hackathon
        team_id: UUID of the team creating the project
        title: Project title
        one_liner: Short description
        description: Detailed description
        repo_url: Repository URL
        demo_url: Demo URL
        video_url: Video URL
    """

    hackathon_id: UUID = Field(..., description="Hackathon ID")
    team_id: UUID = Field(..., description="Team ID")


class ProjectUpdateRequest(BaseModel):
    """
    Request schema for updating a project.

    All fields are optional - only provided fields will be updated.

    Attributes:
        title: New project title
        one_liner: New short description
        description: New detailed description
        repo_url: New repository URL
        demo_url: New demo URL
        video_url: New video URL
    """

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    one_liner: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = Field(None, max_length=5000)
    repo_url: Optional[str] = Field(None, max_length=500)
    demo_url: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Ensure title is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Project title cannot be empty or whitespace")
        return v.strip() if v else None

    @field_validator("repo_url", "demo_url", "video_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v is not None:
            v = v.strip()
            if v and not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("URL must start with http:// or https://")
        return v


class ProjectStatusUpdateRequest(BaseModel):
    """
    Request schema for updating project status.

    Attributes:
        status: New project status (IDEA, BUILDING, SUBMITTED)
    """

    status: ProjectStatus = Field(..., description="New project status")


class ProjectResponse(ProjectBase):
    """
    Response schema for a project.

    Attributes:
        project_id: Unique project identifier
        hackathon_id: UUID of the hackathon
        team_id: UUID of the team
        title: Project title
        one_liner: Short description
        description: Detailed description
        status: Current project status
        repo_url: Repository URL
        demo_url: Demo URL
        video_url: Video URL
        created_at: Timestamp when project was created
        updated_at: Timestamp when project was last updated
    """

    project_id: UUID
    hackathon_id: UUID
    team_id: UUID
    status: ProjectStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """
    Response schema for project listing.

    Attributes:
        projects: List of projects
        total: Total number of projects
        skip: Number of records skipped
        limit: Maximum number of records returned
    """

    projects: List[ProjectResponse]
    total: int
    skip: int = 0
    limit: int = 100


class ProjectDetailResponse(ProjectResponse):
    """
    Response schema for detailed project view.

    Includes all project fields plus potential team information.

    Attributes:
        project_id: Unique project identifier
        hackathon_id: UUID of the hackathon
        team_id: UUID of the team
        title: Project title
        one_liner: Short description
        description: Detailed description
        status: Current project status
        repo_url: Repository URL
        demo_url: Demo URL
        video_url: Video URL
        created_at: Timestamp when project was created
        updated_at: Timestamp when project was last updated
    """

    pass


# Success Response Schema
class SuccessResponse(BaseModel):
    """
    Standard success response schema.

    Attributes:
        success: Success status (always True)
        message: Optional success message
    """

    success: bool = True
    message: Optional[str] = None


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
