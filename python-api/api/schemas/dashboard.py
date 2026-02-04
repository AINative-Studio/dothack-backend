"""
Dashboard API Schemas

Pydantic models for dashboard aggregation endpoints.
Provides role-based views for organizers, builders, and judges.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str
    detail: str
    status_code: int


# Organizer Dashboard Schemas
class OrganizerHackathonSummary(BaseModel):
    """Summary of a hackathon for organizer dashboard."""

    hackathon_id: UUID
    name: str
    status: str
    start_date: datetime
    end_date: datetime
    participant_count: int = Field(default=0, description="Total participants")
    team_count: int = Field(default=0, description="Total teams")
    submission_count: int = Field(default=0, description="Total submissions")


class OrganizerDashboardResponse(BaseModel):
    """Organizer dashboard with hackathon management overview."""

    my_hackathons: List[OrganizerHackathonSummary] = Field(
        default_factory=list, description="Hackathons organized by user"
    )
    total_participants: int = Field(
        default=0, description="Total participants across all hackathons"
    )
    total_teams: int = Field(default=0, description="Total teams across all hackathons")
    total_submissions: int = Field(
        default=0, description="Total submissions across all hackathons"
    )
    pending_judgments: int = Field(
        default=0, description="Submissions awaiting judge scores"
    )


# Builder Dashboard Schemas
class BuilderHackathonSummary(BaseModel):
    """Summary of a hackathon for builder dashboard."""

    hackathon_id: UUID
    name: str
    status: str
    start_date: datetime
    end_date: datetime
    registration_deadline: Optional[datetime] = None
    location: str
    my_role: str = Field(default="builder", description="User's role in hackathon")


class BuilderTeamSummary(BaseModel):
    """Summary of a team for builder dashboard."""

    team_id: UUID
    name: str
    hackathon_id: UUID
    hackathon_name: str
    status: str
    member_count: int
    my_role: str = Field(default="MEMBER", description="User's role in team")


class BuilderSubmissionSummary(BaseModel):
    """Summary of a submission for builder dashboard."""

    submission_id: UUID
    project_id: UUID
    project_name: str
    team_id: UUID
    team_name: str
    hackathon_id: UUID
    hackathon_name: str
    submitted_at: datetime
    status: str


class UpcomingDeadline(BaseModel):
    """Upcoming deadline for builder dashboard."""

    hackathon_id: UUID
    hackathon_name: str
    deadline_type: str = Field(description="Type of deadline (registration, submission)")
    deadline: datetime
    days_remaining: int


class BuilderDashboardResponse(BaseModel):
    """Builder dashboard with participation overview."""

    registered_hackathons: List[BuilderHackathonSummary] = Field(
        default_factory=list, description="Hackathons user has joined"
    )
    my_teams: List[BuilderTeamSummary] = Field(
        default_factory=list, description="Teams user is part of"
    )
    my_submissions: List[BuilderSubmissionSummary] = Field(
        default_factory=list, description="Projects user has submitted"
    )
    upcoming_deadlines: List[UpcomingDeadline] = Field(
        default_factory=list, description="Upcoming deadlines sorted by date"
    )


# Judge Dashboard Schemas
class JudgeHackathonSummary(BaseModel):
    """Summary of a hackathon for judge dashboard."""

    hackathon_id: UUID
    name: str
    status: str
    start_date: datetime
    end_date: datetime
    assigned_submissions: int = Field(
        default=0, description="Submissions assigned to judge"
    )
    completed_judgments: int = Field(
        default=0, description="Submissions already judged"
    )


class PendingSubmission(BaseModel):
    """Pending submission for judge dashboard."""

    submission_id: UUID
    project_id: UUID
    project_name: str
    team_id: UUID
    team_name: str
    hackathon_id: UUID
    hackathon_name: str
    submitted_at: datetime
    track_id: Optional[UUID] = None


class JudgeDashboardResponse(BaseModel):
    """Judge dashboard with judging assignments overview."""

    assigned_hackathons: List[JudgeHackathonSummary] = Field(
        default_factory=list, description="Hackathons where user is a judge"
    )
    submissions_to_judge: int = Field(
        default=0, description="Total pending submissions to judge"
    )
    completed_judgments: int = Field(
        default=0, description="Total completed judgments"
    )
    pending_submissions: List[PendingSubmission] = Field(
        default_factory=list, description="Submissions awaiting judgment"
    )


# Hackathon Overview Dashboard Schemas
class HackathonStats(BaseModel):
    """Statistics for hackathon overview."""

    participant_count: int = Field(default=0, description="Total participants")
    team_count: int = Field(default=0, description="Total teams")
    submission_count: int = Field(default=0, description="Total submissions")
    builder_count: int = Field(default=0, description="Total builders")
    judge_count: int = Field(default=0, description="Total judges")
    track_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Submissions by track"
    )


class RecentActivity(BaseModel):
    """Recent activity entry for hackathon overview."""

    activity_type: str = Field(
        description="Type of activity (team_created, submission_made, participant_joined)"
    )
    description: str = Field(description="Human-readable activity description")
    timestamp: datetime
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional activity data"
    )


class HackathonOverviewResponse(BaseModel):
    """Hackathon overview dashboard for organizers."""

    hackathon_id: UUID
    name: str
    description: Optional[str] = None
    status: str
    start_date: datetime
    end_date: datetime
    location: str
    stats: HackathonStats
    recent_activity: List[RecentActivity] = Field(
        default_factory=list, description="Last 10 activities"
    )
