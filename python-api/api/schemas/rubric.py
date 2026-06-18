"""
Pydantic schemas for rubrics endpoints.

Defines request and response models for judging rubrics management.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CriterionSchema(BaseModel):
    """
    Schema for a single criterion in a rubric.

    Attributes:
        name: Criterion name (e.g., 'Innovation', 'Technical Implementation')
        description: Detailed description of what this criterion evaluates
        max_score: Maximum points available for this criterion
        weight: Weight factor for this criterion (all weights must sum to 1.0)
    """
    name: str = Field(..., min_length=1, max_length=100, description="Criterion name")
    description: str = Field(..., min_length=1, max_length=1000, description="Criterion description")
    max_score: float = Field(..., gt=0, le=100, description="Maximum score for this criterion")
    weight: float = Field(..., gt=0, le=1, description="Weight factor (all weights must sum to 1.0)")

    @field_validator('name', 'description')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure fields are not just whitespace."""
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()


class RubricCreateRequest(BaseModel):
    """
    Request schema for creating a new rubric.

    Attributes:
        name: Rubric name
        criteria: List of criterion definitions
        is_active: Whether this rubric should be set as active immediately
    """
    name: str = Field(..., min_length=1, max_length=200, description="Rubric name")
    criteria: List[CriterionSchema] = Field(..., min_length=1, max_length=20, description="Judging criteria")
    is_active: bool = Field(default=False, description="Set as active rubric")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    @model_validator(mode='after')
    def validate_weights_sum(self) -> 'RubricCreateRequest':
        """Validate that all criterion weights sum to 1.0."""
        if self.criteria:
            total_weight = sum(criterion.weight for criterion in self.criteria)
            # Allow small floating point tolerance
            if abs(total_weight - 1.0) > 0.001:
                raise ValueError(
                    f"Criterion weights must sum to 1.0 (got {total_weight:.4f}). "
                    f"Please adjust the weight values."
                )
        return self


class RubricUpdateRequest(BaseModel):
    """
    Request schema for updating an existing rubric.

    All fields are optional - only provided fields will be updated.

    Attributes:
        name: Rubric name
        criteria: List of criterion definitions
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Rubric name")
    criteria: Optional[List[CriterionSchema]] = Field(None, min_length=1, max_length=20, description="Judging criteria")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip() if v else None

    @model_validator(mode='after')
    def validate_weights_sum(self) -> 'RubricUpdateRequest':
        """Validate that all criterion weights sum to 1.0 if criteria is provided."""
        if self.criteria:
            total_weight = sum(criterion.weight for criterion in self.criteria)
            # Allow small floating point tolerance
            if abs(total_weight - 1.0) > 0.001:
                raise ValueError(
                    f"Criterion weights must sum to 1.0 (got {total_weight:.4f}). "
                    f"Please adjust the weight values."
                )
        return self


class RubricResponse(BaseModel):
    """
    Response schema for a rubric.

    Attributes:
        rubric_id: Unique rubric identifier
        hackathon_id: Associated hackathon identifier
        name: Rubric name
        criteria: List of criterion definitions
        is_active: Whether this is the active rubric for the hackathon
        created_at: Timestamp when rubric was created
        updated_at: Timestamp when rubric was last updated
    """
    rubric_id: UUID
    hackathon_id: UUID
    name: str
    criteria: List[CriterionSchema]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RubricListResponse(BaseModel):
    """
    Response schema for listing rubrics.

    Attributes:
        rubrics: List of rubrics
        total: Total number of rubrics
        hackathon_id: Associated hackathon identifier
    """
    rubrics: List[RubricResponse]
    total: int
    hackathon_id: UUID


class RubricActivateResponse(BaseModel):
    """
    Response schema for activating a rubric.

    Attributes:
        success: Whether activation was successful
        rubric_id: ID of the activated rubric
        message: Confirmation message
    """
    success: bool
    rubric_id: UUID
    message: str


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
