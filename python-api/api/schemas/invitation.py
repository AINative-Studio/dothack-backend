"""
Pydantic schemas for invitation endpoints.

Defines request and response models for hackathon invitation operations.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvitationRole(str, Enum):
    """Valid invitation roles."""
    JUDGE = "JUDGE"
    MENTOR = "MENTOR"
    BUILDER = "BUILDER"


class InvitationStatus(str, Enum):
    """Invitation status enumeration."""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


class InvitationCreateRequest(BaseModel):
    """
    Request schema for creating invitation(s).

    Attributes:
        emails: List of email addresses to invite (1-50 emails)
        role: Role for the invited participants (JUDGE, MENTOR, BUILDER)
    """
    emails: List[str] = Field(..., min_length=1, max_length=50, description="Email addresses to invite")
    role: InvitationRole = Field(..., description="Role for invited participants")

    @field_validator('emails')
    @classmethod
    def validate_emails(cls, v: List[str]) -> List[str]:
        """Validate email format and uniqueness."""
        if not v or len(v) == 0:
            raise ValueError("At least one email is required")

        # Check for duplicates
        unique_emails = set()
        for email in v:
            email = email.strip().lower()
            if not email:
                raise ValueError("Email cannot be empty")
            if '@' not in email or '.' not in email.split('@')[1]:
                raise ValueError(f"Invalid email format: {email}")
            if email in unique_emails:
                raise ValueError(f"Duplicate email: {email}")
            unique_emails.add(email)

        return [email.strip().lower() for email in v]


class InvitationResponse(BaseModel):
    """
    Response schema for a single invitation.

    Attributes:
        invitation_id: Unique invitation identifier
        hackathon_id: Associated hackathon ID
        email: Invitee email address
        role: Assigned role
        token: Secure invitation token
        invited_by: User ID who sent the invitation
        status: Current invitation status
        expires_at: Token expiration timestamp
        accepted_at: Acceptance timestamp (if accepted)
        declined_at: Decline timestamp (if declined)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    invitation_id: str
    hackathon_id: str
    email: str
    role: str
    token: str
    invited_by: str
    status: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationListResponse(BaseModel):
    """
    Response schema for listing invitations.

    Attributes:
        invitations: List of invitation objects
        total: Total number of invitations
        created: Number of invitations created (for create response)
        skipped: Number of invitations skipped (for create response)
    """
    invitations: List[InvitationResponse]
    total: int = Field(..., ge=0, description="Total invitations")
    created: int = Field(default=0, ge=0, description="Number created")
    skipped: int = Field(default=0, ge=0, description="Number skipped")


class InvitationCreateResponse(BaseModel):
    """
    Response schema for bulk invitation creation.

    Attributes:
        invitations: List of created invitations
        created_count: Number of invitations created
        skipped_count: Number of invitations skipped (duplicates)
        skipped_emails: List of emails that were skipped
    """
    invitations: List[InvitationResponse]
    created_count: int = Field(..., ge=0)
    skipped_count: int = Field(..., ge=0)
    skipped_emails: List[str] = Field(default_factory=list)


class InvitationTokenRequest(BaseModel):
    """
    Request schema for accepting/declining invitation by token.

    Attributes:
        token: Invitation token from email link
    """
    token: str = Field(..., min_length=32, max_length=256, description="Invitation token")


class InvitationAcceptRequest(BaseModel):
    """
    Request schema for accepting invitation.

    Attributes:
        token: Invitation token
        email: Email of the user accepting
        name: Name of the user accepting
    """
    token: str = Field(..., min_length=1, max_length=256, description="Invitation token")
    email: str = Field(..., description="Email of the user accepting")
    name: str = Field(..., description="Name of the user accepting")


class InvitationDeclineRequest(BaseModel):
    """
    Request schema for declining invitation.

    Attributes:
        token: Invitation token
    """
    token: str = Field(..., min_length=1, max_length=256, description="Invitation token")


class InvitationActionResponse(BaseModel):
    """
    Response schema for invitation actions (accept/decline/resend).

    Attributes:
        success: Whether action was successful
        message: Result message
        invitation: Updated invitation object (optional)
    """
    success: bool
    message: str
    invitation: Optional[InvitationResponse] = None


class InvitationDeleteResponse(BaseModel):
    """
    Response schema for invitation cancellation.

    Attributes:
        success: Whether cancellation was successful
        invitation_id: ID of cancelled invitation
        message: Confirmation message
    """
    success: bool
    invitation_id: str
    message: str


class ErrorResponse(BaseModel):
    """
    Standard error response schema.

    Attributes:
        error: Error type/message
        detail: Additional error details
        status_code: HTTP status code
    """
    error: str
    detail: Optional[str] = None
    status_code: int
