"""
RLHF API Schemas

Request and response models for RLHF (Reinforcement Learning from Human Feedback)
feedback collection endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class LogInteractionRequest(BaseModel):
    """Request to log an AI interaction for RLHF tracking."""

    prompt: str = Field(..., description="User's input/request", min_length=1)
    response: str = Field(..., description="AI's response/suggestion", min_length=1)
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context (user_id, hackathon_id, feature_type, etc.)",
    )
    agent_id: Optional[str] = Field(
        None,
        description="Agent identifier (defaults to 'dothack_backend')",
    )
    session_id: Optional[str] = Field(
        None,
        description="Session identifier for conversation tracking",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Recommend submissions for judge-123 in hackathon-456",
                "response": "Recommended 5 submissions based on judge's expertise in AI/ML",
                "context": {
                    "user_id": "judge-123",
                    "hackathon_id": "hack-456",
                    "feature_type": "judge_recommendations",
                    "recommended_count": 5,
                },
                "agent_id": "recommendations_service",
                "session_id": "sess-abc-123",
            }
        }


class LogInteractionResponse(BaseModel):
    """Response after logging an interaction."""

    success: bool
    interaction_id: str
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "interaction_id": "int-123-abc-456",
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }


class SubmitFeedbackRequest(BaseModel):
    """Request to submit user feedback on an AI interaction."""

    interaction_id: str = Field(..., description="ID of the interaction being rated")
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
        max_length=1000,
        description="Optional user comment or explanation",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata (e.g., outcome, action_taken)",
    )

    @validator("rating")
    def validate_rating(cls, v, values):
        """Validate that rating is provided if feedback_type is 'rating'."""
        if values.get("feedback_type") == "rating" and v is None:
            raise ValueError("Rating is required when feedback_type is 'rating'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "interaction_id": "int-123-abc-456",
                "feedback_type": "rating",
                "rating": 5,
                "comment": "Perfect recommendations! All submissions were highly relevant.",
                "metadata": {
                    "action_taken": "reviewed_all",
                    "outcome": "successful",
                },
            }
        }


class SubmitFeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    success: bool
    interaction_id: str
    feedback_tracked: bool
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "interaction_id": "int-123-abc-456",
                "feedback_tracked": True,
                "timestamp": "2024-01-15T10:35:00Z",
            }
        }


class InteractionDetails(BaseModel):
    """Details of a specific RLHF interaction."""

    interaction_id: str
    prompt: str
    response: str
    context: Dict[str, Any]
    agent_id: str
    session_id: Optional[str] = None
    created_at: datetime
    feedback: Optional[Dict[str, Any]] = Field(
        None,
        description="Feedback data if available",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "interaction_id": "int-123-abc-456",
                "prompt": "Recommend submissions for judge-123",
                "response": "Recommended 5 submissions based on expertise",
                "context": {
                    "user_id": "judge-123",
                    "hackathon_id": "hack-456",
                    "feature_type": "judge_recommendations",
                },
                "agent_id": "recommendations_service",
                "session_id": "sess-abc-123",
                "created_at": "2024-01-15T10:30:00Z",
                "feedback": {
                    "feedback_type": "rating",
                    "rating": 5,
                    "comment": "Perfect recommendations!",
                    "submitted_at": "2024-01-15T10:35:00Z",
                },
            }
        }


class FeedbackStats(BaseModel):
    """Statistics about feedback collected."""

    thumbs_up_count: int = Field(..., ge=0)
    thumbs_down_count: int = Field(..., ge=0)
    rating_count: int = Field(..., ge=0)
    average_rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    feedback_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of interactions with feedback",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "thumbs_up_count": 45,
                "thumbs_down_count": 5,
                "rating_count": 30,
                "average_rating": 4.2,
                "feedback_rate": 0.75,
            }
        }


class TopIssue(BaseModel):
    """A common issue or complaint from feedback."""

    issue_category: str
    count: int = Field(..., ge=0)
    example_comments: List[str] = Field(..., max_items=3)
    severity: str = Field(
        ...,
        pattern="^(low|medium|high|critical)$",
        description="Issue severity level",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "issue_category": "irrelevant_recommendations",
                "count": 12,
                "example_comments": [
                    "Recommendations didn't match my expertise",
                    "Suggested submissions were not in my domain",
                    "Poor relevance to my interests",
                ],
                "severity": "medium",
            }
        }


class ImprovementSuggestion(BaseModel):
    """AI-generated improvement suggestion based on feedback."""

    category: str = Field(..., description="Category of improvement")
    suggestion: str = Field(..., description="Detailed suggestion text")
    priority: str = Field(
        ...,
        pattern="^(low|medium|high)$",
        description="Improvement priority",
    )
    estimated_impact: str = Field(
        ...,
        pattern="^(low|medium|high)$",
        description="Expected impact if implemented",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "category": "recommendation_quality",
                "suggestion": "Improve judge expertise matching by incorporating past evaluation history and scores",
                "priority": "high",
                "estimated_impact": "high",
            }
        }


class RLHFSummaryReport(BaseModel):
    """Comprehensive RLHF summary report."""

    time_range: str = Field(..., description="Time range for report")
    generated_at: datetime
    total_interactions: int = Field(..., ge=0)
    feedback_stats: FeedbackStats
    top_issues: List[TopIssue] = Field(
        ...,
        max_items=10,
        description="Top issues identified from feedback",
    )
    improvement_suggestions: List[ImprovementSuggestion] = Field(
        ...,
        max_items=10,
        description="AI-generated improvement suggestions",
    )
    feature_breakdown: Optional[Dict[str, Any]] = Field(
        None,
        description="Breakdown by feature type (recommendations, search, etc.)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "time_range": "week",
                "generated_at": "2024-01-15T12:00:00Z",
                "total_interactions": 250,
                "feedback_stats": {
                    "thumbs_up_count": 180,
                    "thumbs_down_count": 20,
                    "rating_count": 150,
                    "average_rating": 4.3,
                    "feedback_rate": 0.8,
                },
                "top_issues": [
                    {
                        "issue_category": "irrelevant_recommendations",
                        "count": 12,
                        "example_comments": ["Not relevant to my expertise"],
                        "severity": "medium",
                    }
                ],
                "improvement_suggestions": [
                    {
                        "category": "recommendation_quality",
                        "suggestion": "Improve expertise matching algorithm",
                        "priority": "high",
                        "estimated_impact": "high",
                    }
                ],
                "feature_breakdown": {
                    "judge_recommendations": {"total": 150, "avg_rating": 4.5},
                    "team_suggestions": {"total": 100, "avg_rating": 4.0},
                },
            }
        }


class ListInteractionsResponse(BaseModel):
    """Response for listing interactions."""

    interactions: List[InteractionDetails]
    total_count: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)
    has_more: bool

    class Config:
        json_schema_extra = {
            "example": {
                "interactions": [
                    {
                        "interaction_id": "int-123",
                        "prompt": "Recommend submissions",
                        "response": "Here are 5 recommendations",
                        "context": {"user_id": "judge-123"},
                        "agent_id": "recommendations_service",
                        "created_at": "2024-01-15T10:30:00Z",
                        "feedback": {
                            "feedback_type": "rating",
                            "rating": 5,
                        },
                    }
                ],
                "total_count": 250,
                "limit": 100,
                "offset": 0,
                "has_more": True,
            }
        }
