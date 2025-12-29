"""
Search API Models

Request and response schemas for semantic search endpoints.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# Request Models


class SearchRequest(BaseModel):
    """Universal search request across all hackathons."""

    query: str = Field(
        ...,
        description="Natural language search query",
        min_length=1,
        max_length=500,
        examples=["machine learning healthcare projects", "blockchain voting system"],
    )
    entity_type: Optional[Literal["submission", "project", "team", "hackathon"]] = Field(
        None,
        description="Filter by entity type (submission, project, team, hackathon)",
    )
    status: Optional[str] = Field(
        None,
        description="Filter by status (e.g., SUBMITTED, DRAFT, LIVE)",
        max_length=50,
    )
    limit: int = Field(
        10,
        description="Maximum number of results to return",
        ge=1,
        le=100,
    )
    offset: int = Field(
        0,
        description="Number of results to skip (pagination)",
        ge=0,
    )
    similarity_threshold: Optional[float] = Field(
        None,
        description="Minimum similarity score (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
    )


class HackathonSearchRequest(BaseModel):
    """Search request within a specific hackathon."""

    query: str = Field(
        ...,
        description="Natural language search query",
        min_length=1,
        max_length=500,
        examples=["AI-powered recommendation engine", "sustainable energy solution"],
    )
    entity_type: Optional[Literal["submission", "project", "team"]] = Field(
        None,
        description="Filter by entity type (submission, project, team)",
    )
    track_id: Optional[str] = Field(
        None,
        description="Filter by track ID",
    )
    status: Optional[str] = Field(
        None,
        description="Filter by status (e.g., SUBMITTED, DRAFT)",
        max_length=50,
    )
    limit: int = Field(
        10,
        description="Maximum number of results to return",
        ge=1,
        le=100,
    )
    offset: int = Field(
        0,
        description="Number of results to skip (pagination)",
        ge=0,
    )
    similarity_threshold: Optional[float] = Field(
        0.5,
        description="Minimum similarity score (0.0 - 1.0)",
        ge=0.0,
        le=1.0,
    )


# Response Models


class SearchResultMetadata(BaseModel):
    """Metadata for a search result."""

    entity_type: str = Field(..., description="Type of entity (submission, project, team, hackathon)")
    hackathon_id: Optional[str] = Field(None, description="Hackathon ID")
    track_id: Optional[str] = Field(None, description="Track ID")
    team_id: Optional[str] = Field(None, description="Team ID")
    status: Optional[str] = Field(None, description="Entity status")
    title: Optional[str] = Field(None, description="Title or name")
    description: Optional[str] = Field(None, description="Description or summary")
    tags: Optional[list[str]] = Field(None, description="Tags or categories")
    submitted_at: Optional[str] = Field(None, description="Submission timestamp")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class SearchResult(BaseModel):
    """Individual search result."""

    id: str = Field(..., description="Entity ID")
    score: float = Field(
        ...,
        description="Similarity score (0.0 - 1.0, higher is more relevant)",
        ge=0.0,
        le=1.0,
    )
    metadata: SearchResultMetadata = Field(
        ...,
        description="Entity metadata with contextual information",
    )


class SearchResponse(BaseModel):
    """Search response with results and pagination info."""

    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of matching results")
    results: list[SearchResult] = Field(
        ...,
        description="Search results sorted by relevance (score descending)",
    )
    limit: int = Field(..., description="Maximum results per page")
    offset: int = Field(..., description="Current offset for pagination")
    has_more: bool = Field(
        ...,
        description="Whether there are more results available",
    )
    execution_time_ms: Optional[float] = Field(
        None,
        description="Search execution time in milliseconds",
    )


class HackathonSearchResponse(SearchResponse):
    """Search response scoped to a specific hackathon."""

    hackathon_id: str = Field(..., description="Hackathon ID for scoped search")
