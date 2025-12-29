"""
Pydantic schemas for judging endpoints.

Defines request and response models for submission scoring,
leaderboard, and ranking functionality.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# Score Submission Schemas
class ScoreSubmitRequest(BaseModel):
    """
    Request schema for submitting a score for a submission.

    Attributes:
        judge_id: UUID of the judge submitting the score
        criteria: Name of the judging criteria (e.g., 'innovation', 'technical', 'design')
        score: Numeric score value (0-100)
        comment: Optional feedback comment from the judge
    """
    judge_id: UUID = Field(..., description="UUID of the judge")
    criteria: str = Field(..., min_length=1, max_length=100, description="Judging criteria name")
    score: float = Field(..., ge=0, le=100, description="Score value between 0 and 100")
    comment: Optional[str] = Field(None, max_length=2000, description="Optional judge feedback")

    @field_validator('criteria')
    @classmethod
    def validate_criteria(cls, v: str) -> str:
        """Ensure criteria is not just whitespace."""
        if not v.strip():
            raise ValueError("Criteria cannot be empty or whitespace")
        return v.strip()


class ScoreResponse(BaseModel):
    """
    Response schema for a single score.

    Attributes:
        id: Unique score identifier
        submission_id: UUID of the submission being scored
        judge_id: UUID of the judge who submitted the score
        criteria: Judging criteria name
        score: Score value
        comment: Judge's feedback comment
        created_at: Timestamp when score was submitted
        updated_at: Timestamp when score was last updated
    """
    id: UUID
    submission_id: UUID
    judge_id: UUID
    criteria: str
    score: float
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScoreListResponse(BaseModel):
    """
    Response schema for listing scores.

    Attributes:
        submission_id: UUID of the submission
        scores: List of scores for this submission
        total_scores: Total number of scores
        average_score: Average score across all criteria
    """
    submission_id: UUID
    scores: List[ScoreResponse]
    total_scores: int
    average_score: Optional[float] = None

    @model_validator(mode='after')
    def calculate_average(self) -> 'ScoreListResponse':
        """Calculate average score if scores are present."""
        if self.scores:
            self.average_score = sum(score.score for score in self.scores) / len(self.scores)
        return self


# Leaderboard Schemas
class LeaderboardEntry(BaseModel):
    """
    Single entry in the hackathon leaderboard.

    Attributes:
        rank: Position in the leaderboard (1-based)
        submission_id: UUID of the submission
        team_name: Name of the team
        project_title: Title of the project
        total_score: Aggregate score across all criteria
        average_score: Average score per criterion
        score_count: Number of scores received
        created_at: Submission creation timestamp
    """
    rank: int = Field(..., ge=1, description="Leaderboard position")
    submission_id: UUID
    team_name: str
    project_title: str
    total_score: float
    average_score: float
    score_count: int = Field(..., ge=0, description="Number of scores")
    created_at: datetime

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    """
    Response schema for hackathon leaderboard.

    Attributes:
        hackathon_id: UUID of the hackathon
        hackathon_name: Name of the hackathon
        entries: List of leaderboard entries, sorted by rank
        total_entries: Total number of submissions with scores
        last_updated: Timestamp of last score update
    """
    hackathon_id: UUID
    hackathon_name: str
    entries: List[LeaderboardEntry]
    total_entries: int
    last_updated: Optional[datetime] = None


# Rankings Schemas
class CriteriaScore(BaseModel):
    """
    Score breakdown for a specific criteria.

    Attributes:
        criteria: Name of the criteria
        score: Score value
        max_score: Maximum possible score for this criteria
    """
    criteria: str
    score: float
    max_score: float = Field(default=100.0, ge=0)


class RankingEntry(BaseModel):
    """
    Detailed ranking entry with score breakdown.

    Attributes:
        rank: Overall rank position
        submission_id: UUID of the submission
        team_name: Name of the team
        project_title: Title of the project
        total_score: Total aggregate score
        criteria_scores: Breakdown by criteria
        judge_count: Number of unique judges who scored
        created_at: Submission timestamp
    """
    rank: int = Field(..., ge=1)
    submission_id: UUID
    team_name: str
    project_title: str
    total_score: float
    criteria_scores: List[CriteriaScore]
    judge_count: int = Field(..., ge=0, description="Number of judges")
    created_at: datetime

    class Config:
        from_attributes = True


class RankingsResponse(BaseModel):
    """
    Response schema for detailed hackathon rankings.

    Attributes:
        hackathon_id: UUID of the hackathon
        hackathon_name: Name of the hackathon
        rankings: List of ranking entries with detailed breakdowns
        total_submissions: Total number of submissions
        criteria_list: List of all judging criteria used
        last_updated: Timestamp of last ranking calculation
    """
    hackathon_id: UUID
    hackathon_name: str
    rankings: List[RankingEntry]
    total_submissions: int
    criteria_list: List[str]
    last_updated: Optional[datetime] = None


# Error Response Schema
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
