"""
Pydantic schemas for track endpoints.

Defines request and response models for track CRUD operations.
Tracks represent hackathon categories/themes.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TrackCreateRequest(BaseModel):
    """
    Request schema for creating a track.

    Attributes:
        name: Track name (required, 3-100 chars)
        description: Detailed description (optional, max 1000 chars)
    """
    name: str = Field(..., min_length=3, max_length=100, description="Track name")
    description: Optional[str] = Field(None, max_length=1000, description="Track description")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()


class TrackUpdateRequest(BaseModel):
    """
    Request schema for updating a track.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: Updated track name
        description: Updated description
    """
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip() if v else None


class TrackResponse(BaseModel):
    """
    Response schema for a single track.

    Attributes:
        track_id: Unique track identifier (UUID)
        hackathon_id: UUID of the parent hackathon
        name: Track name
        description: Track description
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    track_id: str
    hackathon_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrackListResponse(BaseModel):
    """
    Response schema for listing tracks.

    Attributes:
        tracks: List of track objects
        total: Total number of tracks
        hackathon_id: UUID of the parent hackathon
    """
    tracks: List[TrackResponse]
    total: int = Field(..., ge=0, description="Total tracks")
    hackathon_id: str


class TrackDeleteResponse(BaseModel):
    """
    Response schema for track deletion.

    Attributes:
        success: Whether deletion was successful
        track_id: ID of deleted track
        message: Confirmation message
    """
    success: bool
    track_id: str
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
