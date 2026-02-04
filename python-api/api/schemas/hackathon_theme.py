"""
Pydantic schemas for hackathon theme endpoints.

Defines request and response models for theme management and statistics.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class HackathonThemeCreateRequest(BaseModel):
    """
    Request schema for creating a new hackathon theme.

    Attributes:
        theme_name: Unique theme name (required)
        description: Theme description (optional)
        icon: Icon name or emoji (optional)
        display_order: Display order on frontend (optional, auto-assigned if not provided)
    """
    theme_name: str = Field(..., min_length=1, max_length=200, description="Theme name")
    description: Optional[str] = Field(None, max_length=1000, description="Theme description")
    icon: Optional[str] = Field(None, max_length=10, description="Icon emoji or name")
    display_order: Optional[int] = Field(None, ge=1, description="Display order")

    @field_validator('theme_name')
    @classmethod
    def validate_theme_name(cls, v: str) -> str:
        """Ensure theme name is not just whitespace."""
        if not v.strip():
            raise ValueError("Theme name cannot be empty or whitespace")
        return v.strip()


class HackathonThemeUpdateRequest(BaseModel):
    """
    Request schema for updating theme details.

    All fields are optional - only provided fields will be updated.

    Attributes:
        theme_name: New theme name
        description: New description
        icon: New icon
        display_order: New display order
    """
    theme_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    icon: Optional[str] = Field(None, max_length=10)
    display_order: Optional[int] = Field(None, ge=1)

    @field_validator('theme_name')
    @classmethod
    def validate_theme_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure theme name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Theme name cannot be empty or whitespace")
        return v.strip() if v else v


class HackathonThemeOrderUpdateRequest(BaseModel):
    """
    Request schema for updating theme display order.

    Attributes:
        display_order: New display order (required, >= 1)
    """
    display_order: int = Field(..., ge=1, description="Display order")


class HackathonThemeResponse(BaseModel):
    """
    Response schema for a single hackathon theme.

    Attributes:
        id: Unique theme identifier
        theme_name: Theme name
        description: Theme description
        icon: Icon emoji or name
        hackathon_count: Number of hackathons with this theme
        total_prizes: Total prize pool across all hackathons
        display_order: Display order on frontend
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: str
    theme_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    hackathon_count: int = Field(default=0, description="Number of hackathons")
    total_prizes: Decimal = Field(default=Decimal("0.00"), description="Total prize pool")
    display_order: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class HackathonThemeListResponse(BaseModel):
    """
    Response schema for listing themes.

    Attributes:
        themes: List of themes
        total: Total number of themes
    """
    themes: List[HackathonThemeResponse]
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
