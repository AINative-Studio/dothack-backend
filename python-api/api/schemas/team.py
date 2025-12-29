"""
Pydantic schemas for team management endpoints.

Defines request and response models for team CRUD operations,
member management, and team listings.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# Team Member Schemas
class TeamMemberBase(BaseModel):
    """
    Base schema for team member.

    Attributes:
        participant_id: UUID of the participant
        role: Member role (LEAD or MEMBER)
    """

    participant_id: UUID = Field(..., description="UUID of the participant")
    role: Literal["LEAD", "MEMBER"] = Field(..., description="Member role")


class TeamMemberResponse(TeamMemberBase):
    """
    Response schema for team member.

    Attributes:
        id: Unique member identifier
        team_id: UUID of the team
        participant_id: UUID of the participant
        role: Member role
    """

    id: UUID
    team_id: UUID

    class Config:
        from_attributes = True


class AddTeamMemberRequest(BaseModel):
    """
    Request schema for adding a member to a team.

    Attributes:
        participant_id: UUID of the participant to add
        role: Role for the new member (LEAD or MEMBER)
    """

    participant_id: UUID = Field(..., description="Participant to add")
    role: Literal["LEAD", "MEMBER"] = Field(..., description="Member role")


class RemoveTeamMemberRequest(BaseModel):
    """
    Request schema for removing a member from a team.

    Attributes:
        participant_id: UUID of the participant to remove
    """

    participant_id: UUID = Field(..., description="Participant to remove")


# Team Schemas
class TeamBase(BaseModel):
    """
    Base schema for team.

    Attributes:
        name: Team name
        description: Optional team description
        track_id: Optional track ID
    """

    name: str = Field(..., min_length=1, max_length=200, description="Team name")
    description: Optional[str] = Field(
        None, max_length=2000, description="Team description"
    )
    track_id: Optional[UUID] = Field(None, description="Track ID")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Team name cannot be empty or whitespace")
        return v.strip()


class TeamCreateRequest(TeamBase):
    """
    Request schema for creating a new team.

    Attributes:
        hackathon_id: UUID of the hackathon
        name: Team name
        description: Optional team description
        track_id: Optional track ID
    """

    hackathon_id: UUID = Field(..., description="Hackathon ID")


class TeamUpdateRequest(BaseModel):
    """
    Request schema for updating a team.

    All fields are optional - only provided fields will be updated.

    Attributes:
        name: New team name
        description: New team description
        status: New team status
        track_id: New track ID
    """

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[Literal["FORMING", "ACTIVE", "SUBMITTED"]] = Field(None)
    track_id: Optional[UUID] = Field(None)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Team name cannot be empty or whitespace")
        return v.strip() if v else None


class TeamResponse(TeamBase):
    """
    Response schema for a team.

    Attributes:
        team_id: Unique team identifier
        hackathon_id: UUID of the hackathon
        name: Team name
        description: Team description
        track_id: Track ID
        status: Current team status
        created_at: Timestamp when team was created
        members: List of team members (optional)
        member_count: Number of team members (optional)
    """

    team_id: UUID
    hackathon_id: UUID
    status: Literal["FORMING", "ACTIVE", "SUBMITTED"]
    created_at: Optional[datetime] = None
    members: Optional[List[TeamMemberResponse]] = None
    member_count: Optional[int] = None

    class Config:
        from_attributes = True


class TeamListResponse(BaseModel):
    """
    Response schema for team listing.

    Attributes:
        teams: List of teams
        total: Total number of teams
        skip: Number of records skipped
        limit: Maximum number of records returned
    """

    teams: List[TeamResponse]
    total: int
    skip: int = 0
    limit: int = 100


class TeamDetailResponse(TeamResponse):
    """
    Response schema for detailed team view with members.

    Includes all team fields plus member details.

    Attributes:
        team_id: Unique team identifier
        hackathon_id: UUID of the hackathon
        name: Team name
        description: Team description
        track_id: Track ID
        status: Current team status
        created_at: Timestamp when team was created
        members: List of team members with details
        member_count: Total number of members
    """

    members: List[TeamMemberResponse] = Field(default_factory=list)
    member_count: int = 0


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
