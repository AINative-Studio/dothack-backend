"""
Pydantic schemas for project management endpoints.

Defines request and response models for project CRUD operations and status management.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# Type definitions
ProjectStatus = Literal["IDEA", "BUILDING", "SUBMITTED"]


class ProjectCreateRequest(BaseModel):
    """
    Request schema for creating a new project.

    Attributes:
        hackathon_id: UUID of the hackathon
        team_id: UUID of the team creating the project
        title: Project title (required, non-empty)
        one_liner: Short project description (optional)
        repo_url: Repository URL (optional)
        demo_url: Demo/deployment URL (optional)
    """
    hackathon_id: str = Field(..., description="Hackathon UUID")
    team_id: str = Field(..., description="Team UUID")
    title: str = Field(..., min_length=1, max_length=200, description="Project title")
    one_liner: Optional[str] = Field(None, max_length=500, description="Short description")
    repo_url: Optional[str] = Field(None, max_length=500, description="Repository URL")
    demo_url: Optional[str] = Field(None, max_length=500, description="Demo URL")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v.strip():
            raise ValueError("Project title cannot be empty or whitespace")
        return v.strip()

    @field_validator('repo_url', 'demo_url')
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v and not v.strip():
            return None
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.strip() if v else None


class ProjectUpdateRequest(BaseModel):
    """
    Request schema for updating project details.

    All fields are optional - only provided fields will be updated.

    Attributes:
        title: New project title
        one_liner: New short description
        repo_url: New repository URL
        demo_url: New demo URL
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    one_liner: Optional[str] = Field(None, max_length=500)
    repo_url: Optional[str] = Field(None, max_length=500)
    demo_url: Optional[str] = Field(None, max_length=500)

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Ensure title is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Project title cannot be empty or whitespace")
        return v.strip() if v else v

    @field_validator('repo_url', 'demo_url')
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v is not None and not v.strip():
            return None
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.strip() if v else None


class ProjectStatusUpdateRequest(BaseModel):
    """
    Request schema for updating project status.

    Attributes:
        status: New project status (IDEA, BUILDING, or SUBMITTED)
    """
    status: ProjectStatus = Field(..., description="New project status")


class ProjectResponse(BaseModel):
    """
    Response schema for a single project.

    Attributes:
        project_id: Unique project identifier
        hackathon_id: Hackathon UUID
        team_id: Team UUID
        title: Project title
        one_liner: Short description
        status: Current status (IDEA, BUILDING, SUBMITTED)
        repo_url: Repository URL
        demo_url: Demo URL
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    project_id: str
    hackathon_id: str
    team_id: str
    title: str
    one_liner: Optional[str] = None
    status: ProjectStatus
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """
    Response schema for listing projects.

    Attributes:
        projects: List of projects
        total: Total number of projects matching criteria
        skip: Number of records skipped (pagination)
        limit: Maximum number of records returned
    """
    projects: List[ProjectResponse]
    total: int
    skip: int
    limit: int


class ProjectDeleteResponse(BaseModel):
    """
    Response schema for deleting a project.

    Attributes:
        success: Whether the operation succeeded
        message: Success message
    """
    success: bool
    message: str = Field(default="Project deleted successfully")


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
