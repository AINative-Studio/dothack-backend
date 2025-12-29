"""
Search Routes

API endpoints for semantic search across hackathons and entities.
"""

import logging
from uuid import UUID

from api.schemas.search import (
    HackathonSearchRequest,
    HackathonSearchResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchResultMetadata,
)
from fastapi import APIRouter, Depends, status
from integrations.zerodb.client import ZeroDBClient
from services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Search"])


def get_zerodb_client() -> ZeroDBClient:
    """
    Dependency to get ZeroDB client instance.

    Returns:
        Configured ZeroDB client
    """
    return ZeroDBClient()


@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Universal search",
    description="Search across all hackathons, submissions, projects, and teams using natural language queries",
)
async def universal_search(
    request: SearchRequest,
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> SearchResponse:
    """
    Universal semantic search across all entities.

    Searches across:
    - Hackathons
    - Submissions
    - Projects
    - Teams

    Results are sorted by relevance (similarity score, descending).

    Performance target: < 200ms

    **Request Body:**
    - **query**: Natural language search query (required, 1-500 chars)
    - **entity_type**: Filter by type (submission, project, team, hackathon)
    - **status**: Filter by status (e.g., SUBMITTED, DRAFT, LIVE)
    - **limit**: Max results (1-100, default: 10)
    - **offset**: Pagination offset (default: 0)
    - **similarity_threshold**: Min similarity score 0.0-1.0 (optional)

    **Example Queries:**
    - "machine learning healthcare projects"
    - "blockchain voting systems"
    - "AI chatbots for customer support"
    - "sustainable energy solutions"

    **Response:**
    Returns search results with:
    - Similarity scores (0.0 - 1.0, higher = more relevant)
    - Entity metadata (type, hackathon, track, etc.)
    - Pagination info
    - Execution time
    """
    service = SearchService(zerodb)

    search_result = await service.search_all(
        query=request.query,
        entity_type=request.entity_type,
        status=request.status,
        limit=request.limit,
        offset=request.offset,
        similarity_threshold=request.similarity_threshold,
    )

    # Transform results to response models
    results = [
        SearchResult(
            id=r["id"],
            score=r["score"],
            metadata=SearchResultMetadata(**r["metadata"]),
        )
        for r in search_result["results"]
    ]

    total_results = search_result["total_results"]
    has_more = (request.offset + request.limit) < total_results

    return SearchResponse(
        query=request.query,
        total_results=total_results,
        results=results,
        limit=request.limit,
        offset=request.offset,
        has_more=has_more,
        execution_time_ms=search_result.get("execution_time_ms"),
    )


@router.post(
    "/hackathons/{hackathon_id}/search",
    response_model=HackathonSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search within hackathon",
    description="Semantic search scoped to a specific hackathon with track/status filtering",
)
async def hackathon_search(
    hackathon_id: UUID,
    request: HackathonSearchRequest,
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> HackathonSearchResponse:
    """
    Search within a specific hackathon.

    Searches across submissions, projects, and teams within the specified hackathon.
    Results are scoped to the hackathon and can be filtered by track and status.

    Performance target: < 200ms

    **Path Parameters:**
    - **hackathon_id**: UUID of hackathon to search within

    **Request Body:**
    - **query**: Natural language search query (required, 1-500 chars)
    - **entity_type**: Filter by type (submission, project, team)
    - **track_id**: Filter by track ID
    - **status**: Filter by status (e.g., SUBMITTED, DRAFT)
    - **limit**: Max results (1-100, default: 10)
    - **offset**: Pagination offset (default: 0)
    - **similarity_threshold**: Min similarity score 0.0-1.0 (default: 0.5)

    **Example Queries:**
    - "AI-powered recommendation engine"
    - "mobile app with offline support"
    - "data visualization dashboard"

    **Response:**
    Returns hackathon-scoped results with:
    - Similarity scores
    - Entity metadata (type, track, team, etc.)
    - Pagination info
    - Execution time
    - Hackathon ID

    Raises:
    - 404: Hackathon not found
    - 500: Search failed
    - 504: Search timeout
    """
    service = SearchService(zerodb)

    search_result = await service.search_hackathon(
        hackathon_id=str(hackathon_id),
        query=request.query,
        entity_type=request.entity_type,
        track_id=request.track_id,
        status=request.status,
        limit=request.limit,
        offset=request.offset,
        similarity_threshold=request.similarity_threshold,
    )

    # Transform results to response models
    results = [
        SearchResult(
            id=r["id"],
            score=r["score"],
            metadata=SearchResultMetadata(**r["metadata"]),
        )
        for r in search_result["results"]
    ]

    total_results = search_result["total_results"]
    has_more = (request.offset + request.limit) < total_results

    return HackathonSearchResponse(
        query=request.query,
        hackathon_id=str(hackathon_id),
        total_results=total_results,
        results=results,
        limit=request.limit,
        offset=request.offset,
        has_more=has_more,
        execution_time_ms=search_result.get("execution_time_ms"),
    )
