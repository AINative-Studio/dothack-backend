"""
Pydantic schemas for hackathon endpoints.

Defines request and response models for hackathon CRUD operations.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class HackathonStatus(str, Enum):
    """Hackathon status enumeration."""
    DRAFT = "draft"
    UPCOMING = "upcoming"
    ACTIVE = "active"
    JUDGING = "judging"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class HackathonCreateRequest(BaseModel):
    """
    Request schema for creating a hackathon.

    Attributes:
        name: Hackathon name (required, 3-200 chars)
        description: Detailed description (optional, max 5000 chars)
        organizer_id: UUID of the organizer creating the hackathon
        start_date: Start date/time (ISO 8601)
        end_date: End date/time (ISO 8601)
        registration_deadline: Optional registration cutoff date
        max_participants: Optional participant limit
        location: Physical location or "virtual"
        website_url: Optional hackathon website URL
        prizes: Optional prize information (JSON object)
        rules: Optional rules and guidelines (text)
        status: Initial status (defaults to "draft")
    """
    name: str = Field(..., min_length=3, max_length=200, description="Hackathon name")
    description: Optional[str] = Field(None, max_length=5000, description="Hackathon description")
    organizer_id: UUID = Field(..., description="UUID of the organizer")
    start_date: datetime = Field(..., description="Start date/time")
    end_date: datetime = Field(..., description="End date/time")
    registration_deadline: Optional[datetime] = Field(None, description="Registration deadline")
    max_participants: Optional[int] = Field(None, ge=1, description="Maximum participants")
    location: str = Field(..., min_length=1, max_length=200, description="Location or 'virtual'")
    website_url: Optional[str] = Field(None, max_length=500, description="Hackathon website")
    prizes: Optional[dict] = Field(None, description="Prize information (JSON)")
    rules: Optional[str] = Field(None, max_length=10000, description="Rules and guidelines")
    status: HackathonStatus = Field(default=HackathonStatus.DRAFT, description="Hackathon status")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    @field_validator('location')
    @classmethod
    def validate_location(cls, v: str) -> str:
        """Ensure location is not just whitespace."""
        if not v.strip():
            raise ValueError("Location cannot be empty or whitespace")
        return v.strip()

    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v: datetime, info) -> datetime:
        """Ensure end_date is after start_date."""
        if 'start_date' in info.data:
            start_date = info.data['start_date']
            if v <= start_date:
                raise ValueError("end_date must be after start_date")
        return v

    @field_validator('registration_deadline')
    @classmethod
    def validate_registration_deadline(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure registration_deadline is before start_date."""
        if v and 'start_date' in info.data:
            start_date = info.data['start_date']
            if v > start_date:
                raise ValueError("registration_deadline must be before or equal to start_date")
        return v


class HackathonUpdateRequest(BaseModel):
    """
    Request schema for updating a hackathon.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: Updated hackathon name
        description: Updated description
        start_date: Updated start date/time
        end_date: Updated end date/time
        registration_deadline: Updated registration deadline
        max_participants: Updated participant limit
        location: Updated location
        website_url: Updated website URL
        prizes: Updated prize information
        rules: Updated rules
        status: Updated status
    """
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    max_participants: Optional[int] = Field(None, ge=1)
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    website_url: Optional[str] = Field(None, max_length=500)
    prizes: Optional[dict] = None
    rules: Optional[str] = Field(None, max_length=10000)
    status: Optional[HackathonStatus] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip() if v else None

    @field_validator('location')
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        """Ensure location is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Location cannot be empty or whitespace")
        return v.strip() if v else None


class HackathonResponse(BaseModel):
    """
    Response schema for a single hackathon.

    Attributes:
        hackathon_id: Unique hackathon identifier
        name: Hackathon name
        description: Hackathon description
        organizer_id: UUID of the organizer
        start_date: Start date/time
        end_date: End date/time
        registration_deadline: Registration deadline (if set)
        max_participants: Maximum participants (if set)
        location: Location
        website_url: Website URL (if set)
        prizes: Prize information (if set)
        rules: Rules and guidelines (if set)
        status: Current status
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    hackathon_id: str
    name: str
    description: Optional[str]
    organizer_id: str
    start_date: datetime
    end_date: datetime
    registration_deadline: Optional[datetime]
    max_participants: Optional[int]
    location: str
    website_url: Optional[str]
    prizes: Optional[dict]
    rules: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HackathonListResponse(BaseModel):
    """
    Response schema for listing hackathons.

    Attributes:
        hackathons: List of hackathon objects
        total: Total number of hackathons matching filters
        skip: Number of records skipped (pagination)
        limit: Maximum records returned
    """
    hackathons: List[HackathonResponse]
    total: int = Field(..., ge=0, description="Total matching hackathons")
    skip: int = Field(default=0, ge=0, description="Records skipped")
    limit: int = Field(default=100, ge=1, le=1000, description="Records per page")


class HackathonDeleteResponse(BaseModel):
    """
    Response schema for hackathon deletion.

    Attributes:
        success: Whether deletion was successful
        hackathon_id: ID of deleted hackathon
        message: Confirmation message
    """
    success: bool
    hackathon_id: str
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
