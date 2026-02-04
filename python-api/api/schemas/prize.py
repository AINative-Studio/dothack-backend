"""
Pydantic schemas for prize endpoints.

Defines request and response models for hackathon prize management.
Prizes represent awards for hackathon winners with amounts, ranks, and sponsor information.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PrizeCreateRequest(BaseModel):
    """
    Request schema for creating a prize.

    Attributes:
        title: Prize title (required, 3-200 chars)
        description: Detailed description of the prize (optional, max 2000 chars)
        amount: Prize amount in the specified currency (optional)
        currency: Currency code (default: USD, max 10 chars)
        rank: Prize ranking (1=first place, 2=second, etc.)
        track_id: Optional track ID for track-specific prizes
        sponsor_name: Optional sponsor/company name providing the prize
        display_order: Display order for sorting prizes (default: same as rank)
    """
    title: str = Field(..., min_length=3, max_length=200, description="Prize title")
    description: Optional[str] = Field(None, max_length=2000, description="Prize description")
    amount: Optional[Decimal] = Field(None, ge=0, description="Prize amount")
    currency: str = Field(default="USD", max_length=10, description="Currency code")
    rank: int = Field(..., ge=1, le=100, description="Prize ranking (1=first place)")
    track_id: Optional[str] = Field(None, description="Track ID for track-specific prizes")
    sponsor_name: Optional[str] = Field(None, max_length=200, description="Sponsor name")
    display_order: Optional[int] = Field(None, ge=1, description="Display order for sorting")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    @field_validator('sponsor_name')
    @classmethod
    def validate_sponsor_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure sponsor name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Sponsor name cannot be empty or whitespace")
        return v.strip() if v else None

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Ensure currency is uppercase and not whitespace."""
        if not v.strip():
            raise ValueError("Currency cannot be empty or whitespace")
        return v.strip().upper()


class PrizeUpdateRequest(BaseModel):
    """
    Request schema for updating a prize.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        title: Updated prize title
        description: Updated description
        amount: Updated prize amount
        currency: Updated currency code
        rank: Updated prize ranking
        track_id: Updated track ID
        sponsor_name: Updated sponsor name
        display_order: Updated display order
    """
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    rank: Optional[int] = Field(None, ge=1, le=100)
    track_id: Optional[str] = None
    sponsor_name: Optional[str] = Field(None, max_length=200)
    display_order: Optional[int] = Field(None, ge=1)

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Ensure title is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip() if v else None

    @field_validator('sponsor_name')
    @classmethod
    def validate_sponsor_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure sponsor name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Sponsor name cannot be empty or whitespace")
        return v.strip() if v else None

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        """Ensure currency is uppercase and not whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Currency cannot be empty or whitespace")
        return v.strip().upper() if v else None


class PrizeResponse(BaseModel):
    """
    Response schema for a single prize.

    Attributes:
        prize_id: Unique prize identifier (UUID)
        hackathon_id: UUID of the parent hackathon
        title: Prize title
        description: Prize description
        amount: Prize amount
        currency: Currency code
        rank: Prize ranking (1=first place, 2=second, etc.)
        track_id: Optional track ID for track-specific prizes
        sponsor_name: Optional sponsor name
        display_order: Display order for sorting
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    prize_id: str
    hackathon_id: str
    title: str
    description: Optional[str]
    amount: Optional[Decimal]
    currency: str
    rank: int
    track_id: Optional[str]
    sponsor_name: Optional[str]
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PrizeListResponse(BaseModel):
    """
    Response schema for listing prizes.

    Attributes:
        prizes: List of prize objects
        total: Total number of prizes
        hackathon_id: UUID of the parent hackathon
        total_prize_pool: Sum of all prize amounts (grouped by currency)
    """
    prizes: List[PrizeResponse]
    total: int = Field(..., ge=0, description="Total prizes")
    hackathon_id: str
    total_prize_pool: Optional[dict] = Field(
        default=None,
        description="Total prize pool by currency (e.g., {'USD': 50000, 'EUR': 10000})"
    )


class PrizeDeleteResponse(BaseModel):
    """
    Response schema for prize deletion.

    Attributes:
        success: Whether deletion was successful
        prize_id: ID of deleted prize
        message: Confirmation message
    """
    success: bool
    prize_id: str
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
