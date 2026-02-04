"""
Pydantic schemas for featured hackathon endpoints.

Defines request and response models for featured hackathon management.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class FeaturedHackathonCreateRequest(BaseModel):
    """
    Request schema for creating a new featured hackathon entry.

    Attributes:
        hackathon_id: UUID of the hackathon to feature (required)
        display_order: Display order on homepage (required, >= 1)
        featured_until: Optional expiration date for auto-unfeaturing
        is_active: Active status (optional, defaults to true)
    """
    hackathon_id: str = Field(..., min_length=1, description="Hackathon UUID to feature")
    display_order: int = Field(..., ge=1, description="Display order on homepage")
    featured_until: Optional[str] = Field(None, description="Auto-unfeature after this timestamp")
    is_active: Optional[bool] = Field(True, description="Active status")

    @field_validator('hackathon_id')
    @classmethod
    def validate_hackathon_id(cls, v: str) -> str:
        """Ensure hackathon_id is not empty."""
        if not v.strip():
            raise ValueError("Hackathon ID cannot be empty or whitespace")
        return v.strip()

    @field_validator('featured_until')
    @classmethod
    def validate_featured_until(cls, v: Optional[str]) -> Optional[str]:
        """Validate featured_until timestamp format if provided."""
        if v is not None:
            try:
                # Verify it's a valid ISO format timestamp
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError("featured_until must be a valid ISO format timestamp")
        return v


class FeaturedHackathonUpdateRequest(BaseModel):
    """
    Request schema for updating featured hackathon details.

    All fields are optional - only provided fields will be updated.

    Attributes:
        display_order: New display order
        featured_until: New expiration date
        is_active: New active status
    """
    display_order: Optional[int] = Field(None, ge=1)
    featured_until: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)

    @field_validator('featured_until')
    @classmethod
    def validate_featured_until(cls, v: Optional[str]) -> Optional[str]:
        """Validate featured_until timestamp format if provided."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValueError("featured_until must be a valid ISO format timestamp")
        return v


class FeaturedHackathonOrderUpdateRequest(BaseModel):
    """
    Request schema for updating featured hackathon display order.

    Attributes:
        display_order: New display order (required, >= 1)
    """
    display_order: int = Field(..., ge=1, description="Display order")


class FeaturedHackathonResponse(BaseModel):
    """
    Response schema for a single featured hackathon entry.

    Attributes:
        id: Unique featured entry identifier
        hackathon_id: UUID of the featured hackathon
        display_order: Display order on homepage
        featured_until: Optional expiration timestamp
        is_active: Active status
        created_at: Creation timestamp
        updated_at: Last update timestamp
        hackathon: Optional nested hackathon details
    """
    id: str
    hackathon_id: str
    display_order: int
    featured_until: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    hackathon: Optional[dict] = Field(None, description="Nested hackathon details")

    class Config:
        from_attributes = True


class FeaturedHackathonListResponse(BaseModel):
    """
    Response schema for listing featured hackathons.

    Attributes:
        featured: List of featured hackathons
        total: Total number of featured hackathons
    """
    featured: List[FeaturedHackathonResponse]
    total: int


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
