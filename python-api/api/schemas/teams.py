"""
Pydantic schemas for team management endpoints.

Defines request and response models for team CRUD operations
and team member management.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Type definitions
TeamStatus = Literal["FORMING", "ACTIVE", "SUBMITTED"]
MemberRole = Literal["LEAD", "MEMBER"]


# Team Create/Update Schemas
class TeamCreateRequest(BaseModel):
    """
    Request schema for creating a new team.

    Attributes:
        hackathon_id: UUID of the hackathon this team belongs to
        name: Team name (required, non-empty)
        track_id: Optional track UUID
        description: Optional team description
    """
    hackathon_id: str = Field(..., description="Hackathon UUID")
    name: str = Field(..., min_length=1, max_length=200, description="Team name")
    track_id: Optional[str] = Field(None, description="Optional track UUID")
    description: Optional[str] = Field(None, max_length=2000, description="Team description")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Team name cannot be empty or whitespace")
        return v.strip()


class TeamUpdateRequest(BaseModel):
    """
    Request schema for updating team details.

    All fields are optional - only provided fields will be updated.

    Attributes:
        name: New team name
        description: New team description
        status: New team status (FORMING, ACTIVE, SUBMITTED)
        track_id: New track UUID
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Team name")
    description: Optional[str] = Field(None, max_length=2000, description="Team description")
    status: Optional[TeamStatus] = Field(None, description="Team status")
    track_id: Optional[str] = Field(None, description="Track UUID")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Team name cannot be empty or whitespace")
        return v.strip() if v else v


# Team Member Schemas
class TeamMemberAddRequest(BaseModel):
    """
    Request schema for adding a member to a team.

    Attributes:
        participant_id: UUID of the participant to add
        role: Member role (LEAD or MEMBER)
    """
    participant_id: str = Field(..., description="Participant UUID")
    role: MemberRole = Field(default="MEMBER", description="Member role")


class TeamMemberResponse(BaseModel):
    """
    Response schema for a team member.

    Attributes:
        id: Member record UUID
        team_id: Team UUID
        participant_id: Participant UUID
        role: Member role (LEAD or MEMBER)
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    team_id: str
    participant_id: str
    role: MemberRole


# Team Response Schemas
class TeamResponse(BaseModel):
    """
    Response schema for a single team.

    Attributes:
        team_id: Unique team identifier
        hackathon_id: Hackathon UUID this team belongs to
        name: Team name
        status: Team status (FORMING, ACTIVE, SUBMITTED)
        track_id: Optional track UUID
        description: Optional team description
        created_at: Timestamp when team was created
        updated_at: Timestamp when team was last updated
    """
    model_config = ConfigDict(from_attributes=True)

    team_id: str
    hackathon_id: str
    name: str
    status: TeamStatus
    track_id: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TeamDetailResponse(TeamResponse):
    """
    Response schema for team details with members.

    Extends TeamResponse to include member list and count.

    Attributes:
        members: List of team members
        member_count: Total number of team members
    """
    members: List[TeamMemberResponse]
    member_count: int


class TeamListResponse(BaseModel):
    """
    Response schema for listing teams.

    Attributes:
        teams: List of teams
        total: Total number of teams matching criteria
        skip: Number of records skipped (pagination)
        limit: Maximum number of records returned
    """
    teams: List[TeamResponse]
    total: int
    skip: int
    limit: int


# Success Response Schemas
class TeamMemberAddResponse(BaseModel):
    """
    Response schema for adding a team member.

    Attributes:
        id: Member record UUID
        team_id: Team UUID
        participant_id: Participant UUID
        role: Member role
    """
    id: str
    team_id: str
    participant_id: str
    role: MemberRole


class TeamMemberRemoveResponse(BaseModel):
    """
    Response schema for removing a team member.

    Attributes:
        success: Whether the operation succeeded
        message: Success message
    """
    success: bool
    message: str = Field(default="Member removed successfully")


class TeamDeleteResponse(BaseModel):
    """
    Response schema for deleting a team.

    Attributes:
        success: Whether the operation succeeded
        message: Success message
    """
    success: bool
    message: str = Field(default="Team deleted successfully")


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
