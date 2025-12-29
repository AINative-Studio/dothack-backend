"""
Recommendations API Schemas

Request and response models for AI-powered recommendations endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RecommendedSubmissionItem(BaseModel):
    """Individual recommended submission with relevance score."""

    submission_id: str
    team_id: str
    hackathon_id: str
    project_name: str
    description: str
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    status: str
    created_at: datetime
    repository_url: Optional[str] = None
    demo_url: Optional[str] = None
    presentation_url: Optional[str] = None
    track_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "submission_id": "sub-123",
                "team_id": "team-456",
                "hackathon_id": "hack-789",
                "project_name": "AI Healthcare Assistant",
                "description": "An AI-powered chatbot for medical diagnosis",
                "relevance_score": 0.92,
                "status": "SUBMITTED",
                "created_at": "2024-01-15T10:30:00Z",
                "repository_url": "https://github.com/team/project",
                "demo_url": "https://demo.example.com",
            }
        }


class JudgeRecommendationsResponse(BaseModel):
    """Response for judge recommendations."""

    recommended_submissions: List[RecommendedSubmissionItem]
    total_recommended: int = Field(..., ge=0)
    recommendation_reason: str = Field(..., description="Why these were recommended")
    execution_time_ms: Optional[float] = Field(
        None, ge=0, description="Execution time in milliseconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "recommended_submissions": [
                    {
                        "submission_id": "sub-123",
                        "team_id": "team-456",
                        "hackathon_id": "hack-789",
                        "project_name": "AI Healthcare Assistant",
                        "description": "An AI-powered chatbot",
                        "relevance_score": 0.92,
                        "status": "SUBMITTED",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "total_recommended": 1,
                "recommendation_reason": "Based on your highly-rated submissions",
                "execution_time_ms": 145.23,
            }
        }


class SuggestedParticipantItem(BaseModel):
    """Individual participant suggestion with match score."""

    participant_id: str
    hackathon_id: str
    match_score: float = Field(..., ge=0.0, le=1.0, description="Skill match score")
    role: str
    joined_at: datetime
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional participant metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "participant_id": "user-123",
                "hackathon_id": "hack-456",
                "match_score": 0.87,
                "role": "BUILDER",
                "joined_at": "2024-01-10T08:00:00Z",
                "metadata": {
                    "skills": ["Python", "React", "Machine Learning"],
                    "experience_level": "Intermediate",
                },
            }
        }


class TeamSuggestionsRequest(BaseModel):
    """Request for team formation suggestions."""

    desired_skills: Optional[List[str]] = Field(
        None,
        description="Optional list of desired skills to match",
        max_items=10,
    )
    top_k: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of suggestions to return",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "desired_skills": ["Python", "Machine Learning", "React"],
                "top_k": 10,
            }
        }


class TeamSuggestionsResponse(BaseModel):
    """Response for team formation suggestions."""

    suggested_participants: List[SuggestedParticipantItem]
    total_suggested: int = Field(..., ge=0)
    suggestion_reason: str = Field(..., description="Why these were suggested")
    execution_time_ms: Optional[float] = Field(
        None, ge=0, description="Execution time in milliseconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "suggested_participants": [
                    {
                        "participant_id": "user-123",
                        "hackathon_id": "hack-456",
                        "match_score": 0.87,
                        "role": "BUILDER",
                        "joined_at": "2024-01-10T08:00:00Z",
                        "metadata": {"skills": ["Python", "React"]},
                    }
                ],
                "total_suggested": 1,
                "suggestion_reason": "Participants with skills: Python, Machine Learning",
                "execution_time_ms": 132.45,
            }
        }


class RecommendationFeedbackRequest(BaseModel):
    """Request to track feedback on a recommendation."""

    feedback_type: str = Field(
        ...,
        description="Type of feedback: thumbs_up, thumbs_down, or rating",
        pattern="^(thumbs_up|thumbs_down|rating)$",
    )
    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Rating value 1-5 (required if feedback_type is 'rating')",
    )
    comment: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional feedback comment",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "feedback_type": "rating",
                "rating": 5,
                "comment": "Great recommendations, very relevant to my expertise!",
            }
        }


class RecommendationFeedbackResponse(BaseModel):
    """Response after tracking feedback."""

    success: bool
    recommendation_id: str
    feedback_tracked: bool

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "recommendation_id": "rec-123",
                "feedback_tracked": True,
            }
        }
