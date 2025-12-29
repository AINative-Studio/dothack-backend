"""
Participant Management Models

Request and response schemas for participant endpoints.
"""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# Request Models

class JoinHackathonRequest(BaseModel):
    """Request body for joining a hackathon."""

    # No body needed - user comes from auth, hackathon_id from path
    pass


class InviteJudgesRequest(BaseModel):
    """Request body for inviting judges to a hackathon."""

    emails: list[EmailStr] = Field(
        ...,
        description="List of judge email addresses to invite",
        min_length=1,
        max_length=50,
    )
    message: Optional[str] = Field(
        None,
        description="Optional custom invitation message",
        max_length=500,
    )


# Response Models

class ParticipantResponse(BaseModel):
    """Participant information response."""

    id: str = Field(..., description="Participant record ID")
    participant_id: str = Field(..., description="User participant ID")
    hackathon_id: str = Field(..., description="Hackathon ID")
    role: Literal["BUILDER", "ORGANIZER", "JUDGE", "MENTOR"] = Field(
        ..., description="Participant role"
    )
    email: Optional[EmailStr] = Field(None, description="Participant email")
    name: Optional[str] = Field(None, description="Participant name")
    joined_at: str = Field(..., description="ISO timestamp when joined")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class JoinHackathonResponse(BaseModel):
    """Response for joining a hackathon."""

    success: bool = Field(..., description="Whether join was successful")
    participant: ParticipantResponse = Field(
        ..., description="Created participant record"
    )
    message: str = Field(..., description="Success message")


class InviteJudgesResponse(BaseModel):
    """Response for inviting judges."""

    success: bool = Field(..., description="Whether invites were sent")
    invited_count: int = Field(..., description="Number of judges invited")
    invited_emails: list[EmailStr] = Field(..., description="Emails invited")
    message: str = Field(..., description="Success message")


class ListParticipantsResponse(BaseModel):
    """Response for listing participants."""

    hackathon_id: str = Field(..., description="Hackathon ID")
    total_count: int = Field(..., description="Total number of participants")
    participants: list[ParticipantResponse] = Field(
        ..., description="List of participants"
    )


class LeaveHackathonResponse(BaseModel):
    """Response for leaving a hackathon."""

    success: bool = Field(..., description="Whether leave was successful")
    message: str = Field(..., description="Success message")
