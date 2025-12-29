"""
Event Schemas for DotHack Event Stream

Pydantic schemas for validating event data published to ZeroDB Events API.
All events follow a consistent pattern: {resource}.{action}
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BaseEventMetadata(BaseModel):
    """
    Base metadata included in all events.

    Attributes:
        user_id: UUID of the user who triggered the event
        timestamp: ISO 8601 timestamp when event occurred
        correlation_id: Optional correlation ID for tracing related events
        source: Event source identifier (defaults to "dothack-api")
    """
    user_id: str = Field(..., description="User ID who triggered the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for event tracking")
    source: str = Field(default="dothack-api", description="Event source")


class HackathonEventData(BaseModel):
    """
    Event data for hackathon-related events.

    Event Types:
        - hackathon.created: New hackathon was created
        - hackathon.started: Hackathon moved to active status
        - hackathon.closed: Hackathon moved to completed/cancelled status

    Attributes:
        hackathon_id: Unique hackathon identifier
        name: Hackathon name
        status: Current hackathon status
        organizer_id: Organizer user ID
        start_date: Hackathon start date (for created/started events)
        end_date: Hackathon end date (for created/started events)
        metadata: Base event metadata (user_id, timestamp, correlation_id)
    """
    hackathon_id: str = Field(..., description="Hackathon ID")
    name: str = Field(..., description="Hackathon name")
    status: str = Field(..., description="Hackathon status")
    organizer_id: str = Field(..., description="Organizer user ID")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    location: Optional[str] = Field(None, description="Hackathon location")
    metadata: BaseEventMetadata = Field(..., description="Event metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "hackathon_id": "hack-123-abc",
                "name": "AI Hackathon 2024",
                "status": "active",
                "organizer_id": "user-456-def",
                "start_date": "2024-03-01T00:00:00Z",
                "end_date": "2024-03-03T23:59:59Z",
                "location": "San Francisco",
                "metadata": {
                    "user_id": "user-456-def",
                    "timestamp": "2024-03-01T00:00:00Z",
                    "correlation_id": "corr-abc-123",
                    "source": "dothack-api"
                }
            }
        }


class TeamEventData(BaseModel):
    """
    Event data for team-related events.

    Event Types:
        - team.formed: New team was created
        - team.updated: Team information was modified
        - team.member_added: New member joined the team
        - team.member_removed: Member left/was removed from team

    Attributes:
        team_id: Unique team identifier
        hackathon_id: Associated hackathon ID
        name: Team name
        creator_id: Team creator/lead user ID
        status: Team status (FORMING, ACTIVE, SUBMITTED)
        member_count: Current number of team members
        track_id: Optional track ID
        metadata: Base event metadata
    """
    team_id: str = Field(..., description="Team ID")
    hackathon_id: str = Field(..., description="Associated hackathon ID")
    name: str = Field(..., description="Team name")
    creator_id: str = Field(..., description="Team creator/lead ID")
    status: str = Field(..., description="Team status")
    member_count: Optional[int] = Field(None, description="Number of team members")
    track_id: Optional[str] = Field(None, description="Track ID")
    metadata: BaseEventMetadata = Field(..., description="Event metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "team_id": "team-789-xyz",
                "hackathon_id": "hack-123-abc",
                "name": "AI Innovators",
                "creator_id": "user-111-aaa",
                "status": "FORMING",
                "member_count": 1,
                "track_id": "track-ai-ml",
                "metadata": {
                    "user_id": "user-111-aaa",
                    "timestamp": "2024-03-01T10:30:00Z",
                    "correlation_id": "corr-def-456",
                    "source": "dothack-api"
                }
            }
        }


class SubmissionEventData(BaseModel):
    """
    Event data for submission-related events.

    Event Types:
        - submission.created: New submission was created
        - submission.updated: Submission was modified
        - submission.finalized: Submission marked as final

    Attributes:
        submission_id: Unique submission identifier
        hackathon_id: Associated hackathon ID
        team_id: Submitting team ID
        track_id: Submission track ID
        title: Submission title
        status: Submission status (DRAFT, SUBMITTED)
        submitted_by: User ID who submitted
        metadata: Base event metadata
    """
    submission_id: str = Field(..., description="Submission ID")
    hackathon_id: str = Field(..., description="Associated hackathon ID")
    team_id: str = Field(..., description="Team ID")
    track_id: Optional[str] = Field(None, description="Track ID")
    title: str = Field(..., description="Submission title")
    status: str = Field(..., description="Submission status")
    submitted_by: str = Field(..., description="User ID who submitted")
    metadata: BaseEventMetadata = Field(..., description="Event metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "submission_id": "sub-222-bbb",
                "hackathon_id": "hack-123-abc",
                "team_id": "team-789-xyz",
                "track_id": "track-ai-ml",
                "title": "AI-Powered Code Assistant",
                "status": "SUBMITTED",
                "submitted_by": "user-111-aaa",
                "metadata": {
                    "user_id": "user-111-aaa",
                    "timestamp": "2024-03-03T20:00:00Z",
                    "correlation_id": "corr-ghi-789",
                    "source": "dothack-api"
                }
            }
        }


class ScoreEventData(BaseModel):
    """
    Event data for scoring/judging events.

    Event Types:
        - score.submitted: Judge submitted a score for a submission
        - score.updated: Judge updated their score
        - judging.completed: All judging completed for a submission

    Attributes:
        score_id: Unique score identifier
        submission_id: Submission being scored
        hackathon_id: Associated hackathon ID
        judge_id: Judge user ID
        technical_score: Technical score (0-10)
        creativity_score: Creativity score (0-10)
        impact_score: Impact score (0-10)
        presentation_score: Presentation score (0-10)
        total_score: Total/average score
        metadata: Base event metadata
    """
    score_id: str = Field(..., description="Score ID")
    submission_id: str = Field(..., description="Submission ID being scored")
    hackathon_id: str = Field(..., description="Associated hackathon ID")
    judge_id: str = Field(..., description="Judge user ID")
    technical_score: Optional[float] = Field(None, description="Technical score", ge=0, le=10)
    creativity_score: Optional[float] = Field(None, description="Creativity score", ge=0, le=10)
    impact_score: Optional[float] = Field(None, description="Impact score", ge=0, le=10)
    presentation_score: Optional[float] = Field(None, description="Presentation score", ge=0, le=10)
    total_score: Optional[float] = Field(None, description="Total score")
    metadata: BaseEventMetadata = Field(..., description="Event metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "score_id": "score-333-ccc",
                "submission_id": "sub-222-bbb",
                "hackathon_id": "hack-123-abc",
                "judge_id": "judge-444-ddd",
                "technical_score": 8.5,
                "creativity_score": 9.0,
                "impact_score": 7.5,
                "presentation_score": 8.0,
                "total_score": 8.25,
                "metadata": {
                    "user_id": "judge-444-ddd",
                    "timestamp": "2024-03-04T15:30:00Z",
                    "correlation_id": "corr-jkl-012",
                    "source": "dothack-api"
                }
            }
        }


class EventPublishRequest(BaseModel):
    """
    Request schema for publishing events via API endpoint.

    Used when external services need to publish events directly.

    Attributes:
        event_type: Event type (e.g., "hackathon.created")
        data: Event-specific data (must match schema for event_type)
        correlation_id: Optional correlation ID for tracking
    """
    event_type: str = Field(..., description="Event type (resource.action pattern)")
    data: Dict[str, Any] = Field(..., description="Event data payload")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "hackathon.created",
                "data": {
                    "hackathon_id": "hack-123-abc",
                    "name": "AI Hackathon 2024",
                    "status": "draft",
                    "organizer_id": "user-456-def",
                    "metadata": {
                        "user_id": "user-456-def",
                        "timestamp": "2024-03-01T00:00:00Z"
                    }
                }
            }
        }


class EventPublishResponse(BaseModel):
    """
    Response schema for successful event publication.

    Attributes:
        success: Whether event was published successfully
        event_id: Unique event ID from ZeroDB
        event_type: Event type that was published
        timestamp: When the event was published
        message: Success message
    """
    success: bool = Field(True, description="Event published successfully")
    event_id: str = Field(..., description="ZeroDB event ID")
    event_type: str = Field(..., description="Event type published")
    timestamp: datetime = Field(..., description="Publication timestamp")
    message: str = Field(default="Event published successfully", description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "event_id": "evt-555-eee",
                "event_type": "hackathon.created",
                "timestamp": "2024-03-01T00:00:00Z",
                "message": "Event published successfully"
            }
        }
