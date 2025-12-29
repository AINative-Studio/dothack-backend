"""
Search API Endpoints

RESTful API for semantic search of hackathon submissions.
Provides natural language search and similarity-based search.
"""

import logging
from typing import Any, Dict, List, Optional

from api.dependencies import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Query, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from pydantic import BaseModel, Field
from services.search_service import SearchResult, SearchService

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/v1/search", tags=["Search"])


# ============================================================================
# Pydantic Schemas
# ============================================================================


class SearchResultSchema(BaseModel):
    """Schema for a single search result"""
    submission_id: str = Field(..., description="Unique submission identifier")
    hackathon_id: str = Field(..., description="Hackathon identifier")
    title: str = Field(..., description="Project title")
    description: str = Field(..., description="Project description")
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score (0.0 - 1.0)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (track, status, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "submission_id": "sub-123",
                "hackathon_id": "hack-456",
                "title": "AI Healthcare Assistant",
                "description": "An AI-powered tool for medical diagnosis",
                "similarity_score": 0.92,
                "metadata": {
                    "track_id": "ai-ml",
                    "status": "SUBMITTED",
                    "team_id": "team-789"
                }
            }
        }


class SearchResponse(BaseModel):
    """Response schema for search endpoints"""
    results: List[SearchResultSchema] = Field(
        ...,
        description="List of search results"
    )
    count: int = Field(..., description="Number of results returned")
    query: Optional[str] = Field(None, description="Original search query")
    hackathon_id: str = Field(..., description="Hackathon searched")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "submission_id": "sub-123",
                        "hackathon_id": "hack-456",
                        "title": "AI Healthcare Assistant",
                        "description": "An AI-powered tool",
                        "similarity_score": 0.92,
                        "metadata": {"track_id": "ai-ml"}
                    }
                ],
                "count": 1,
                "query": "AI healthcare solutions",
                "hackathon_id": "hack-456"
            }
        }


class PaginatedSearchResponse(BaseModel):
    """Response schema for paginated search"""
    results: List[SearchResultSchema]
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=50, description="Results per page")
    total: int = Field(..., description="Total number of results")
    has_more: bool = Field(..., description="Whether more results exist")
    query: Optional[str] = Field(None, description="Original search query")
    hackathon_id: str = Field(..., description="Hackathon searched")


class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Search query cannot be empty",
                "error_code": "INVALID_QUERY"
            }
        }


# ============================================================================
# Dependency Functions
# ============================================================================


def get_zerodb_client() -> ZeroDBClient:
    """
    Dependency to get ZeroDB client instance.

    Returns:
        Configured ZeroDBClient instance
    """
    from config import settings

    return ZeroDBClient(
        api_key=settings.ZERODB_API_KEY,
        project_id=settings.ZERODB_PROJECT_ID,
        base_url=settings.ZERODB_BASE_URL,
        timeout=settings.ZERODB_TIMEOUT,
    )


def get_search_service(
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client)
) -> SearchService:
    """
    Dependency to get SearchService instance.

    Args:
        zerodb_client: ZeroDB client dependency

    Returns:
        Configured SearchService instance
    """
    return SearchService(zerodb_client)


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "/submissions",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search submissions by natural language query",
    description=(
        "Search hackathon submissions using natural language queries. "
        "Results are ranked by semantic similarity to the query."
    ),
    responses={
        200: {
            "description": "Search completed successfully",
            "model": SearchResponse,
        },
        400: {
            "description": "Invalid query or parameters",
            "model": ErrorResponse,
        },
        401: {
            "description": "Unauthorized - invalid or missing authentication",
            "model": ErrorResponse,
        },
        404: {
            "description": "Hackathon not found",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def search_submissions(
    query: str = Query(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language search query",
        example="AI-powered healthcare solutions"
    ),
    hackathon_id: str = Query(
        ...,
        description="Hackathon ID to search within",
        example="hack-123"
    ),
    top_k: int = Query(
        10,
        ge=1,
        le=50,
        description="Number of results to return (max 50)",
        example=10
    ),
    track_id: Optional[str] = Query(
        None,
        description="Filter by track ID",
        example="ai-ml"
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by submission status (DRAFT, SUBMITTED, SCORED)",
        example="SUBMITTED"
    ),
    min_similarity: float = Query(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold (0.0 - 1.0)",
        example=0.5
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    """
    Search submissions using natural language query.

    Performs semantic search across submission titles and descriptions
    to find the most relevant projects based on the query.

    **Authentication Required**: Yes (Bearer token)

    **Query Parameters**:
    - **query**: Natural language search query (required)
    - **hackathon_id**: Hackathon to search within (required)
    - **top_k**: Number of results (default: 10, max: 50)
    - **track_id**: Optional track filter
    - **status**: Optional status filter (DRAFT, SUBMITTED, SCORED)
    - **min_similarity**: Minimum similarity score (default: 0.5)

    **Example**:
    ```
    GET /v1/search/submissions?query=AI+healthcare&hackathon_id=hack-123&top_k=5
    ```
    """
    try:
        # Build filters
        filters = {}
        if track_id:
            filters["track_id"] = track_id
        if status:
            # Validate status
            if status not in ["DRAFT", "SUBMITTED", "SCORED"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}. Must be DRAFT, SUBMITTED, or SCORED"
                )
            filters["status"] = status

        # Perform search
        results = await search_service.search_by_query(
            query=query,
            hackathon_id=hackathon_id,
            top_k=top_k,
            filters=filters if filters else None,
            min_similarity=min_similarity
        )

        # Convert to schema
        result_schemas = [
            SearchResultSchema(
                submission_id=r.submission_id,
                hackathon_id=r.hackathon_id,
                title=r.title,
                description=r.description,
                similarity_score=r.similarity_score,
                metadata=r.metadata
            )
            for r in results
        ]

        logger.info(
            f"User {current_user.get('user_id')} searched '{query}' "
            f"in hackathon {hackathon_id}, found {len(results)} results"
        )

        return SearchResponse(
            results=result_schemas,
            count=len(result_schemas),
            query=query,
            hackathon_id=hackathon_id
        )

    except ValueError as e:
        logger.warning(f"Invalid search parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ZeroDBNotFound as e:
        logger.error(f"Hackathon not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hackathon {hackathon_id} not found"
        )
    except ZeroDBTimeoutError as e:
        logger.error(f"Search timeout: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Search request timed out. Please try again."
        )
    except ZeroDBError as e:
        logger.error(f"ZeroDB error during search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search"
        )


@router.get(
    "/submissions/paginated",
    response_model=PaginatedSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search submissions with pagination",
    description="Search submissions with pagination support for large result sets"
)
async def search_submissions_paginated(
    query: str = Query(..., description="Natural language search query"),
    hackathon_id: str = Query(..., description="Hackathon ID to search within"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=50, description="Results per page"),
    track_id: Optional[str] = Query(None, description="Filter by track ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    min_similarity: float = Query(0.5, ge=0.0, le=1.0, description="Min similarity"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service)
) -> PaginatedSearchResponse:
    """
    Search submissions with pagination.

    **Authentication Required**: Yes (Bearer token)
    """
    try:
        # Build filters
        filters = {}
        if track_id:
            filters["track_id"] = track_id
        if status:
            if status not in ["DRAFT", "SUBMITTED", "SCORED"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
            filters["status"] = status

        # Perform paginated search
        paginated = await search_service.search_with_pagination(
            query=query,
            hackathon_id=hackathon_id,
            page=page,
            page_size=page_size,
            filters=filters if filters else None,
            min_similarity=min_similarity
        )

        # Convert results to schema
        result_schemas = [
            SearchResultSchema(
                submission_id=r.submission_id,
                hackathon_id=r.hackathon_id,
                title=r.title,
                description=r.description,
                similarity_score=r.similarity_score,
                metadata=r.metadata
            )
            for r in paginated["results"]
        ]

        return PaginatedSearchResponse(
            results=result_schemas,
            page=paginated["page"],
            page_size=paginated["page_size"],
            total=paginated["total"],
            has_more=paginated["has_more"],
            query=query,
            hackathon_id=hackathon_id
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ZeroDBError as e:
        logger.error(f"ZeroDB error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/submissions/{submission_id}/similar",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Find similar submissions",
    description=(
        "Find submissions similar to a given submission based on "
        "semantic similarity of content."
    ),
    responses={
        200: {
            "description": "Similar submissions found",
            "model": SearchResponse,
        },
        400: {
            "description": "Invalid parameters",
            "model": ErrorResponse,
        },
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
        404: {
            "description": "Submission not found",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def find_similar_submissions(
    submission_id: str,
    hackathon_id: str = Query(
        ...,
        description="Hackathon ID for context",
        example="hack-123"
    ),
    top_k: int = Query(
        10,
        ge=1,
        le=50,
        description="Number of similar submissions to return",
        example=10
    ),
    track_id: Optional[str] = Query(
        None,
        description="Filter by track ID"
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by submission status"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    """
    Find submissions similar to the given submission.

    Retrieves the embedding for the specified submission and searches
    for other submissions with similar content.

    **Authentication Required**: Yes (Bearer token)

    **Path Parameters**:
    - **submission_id**: ID of the reference submission

    **Query Parameters**:
    - **hackathon_id**: Hackathon context (required)
    - **top_k**: Number of results (default: 10, max: 50)
    - **track_id**: Optional track filter
    - **status**: Optional status filter

    **Example**:
    ```
    GET /v1/search/submissions/sub-123/similar?hackathon_id=hack-456&top_k=5
    ```
    """
    try:
        # Build filters
        filters = {}
        if track_id:
            filters["track_id"] = track_id
        if status:
            if status not in ["DRAFT", "SUBMITTED", "SCORED"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
            filters["status"] = status

        # Find similar submissions
        results = await search_service.find_similar_submissions(
            submission_id=submission_id,
            hackathon_id=hackathon_id,
            top_k=top_k,
            filters=filters if filters else None
        )

        # Convert to schema
        result_schemas = [
            SearchResultSchema(
                submission_id=r.submission_id,
                hackathon_id=r.hackathon_id,
                title=r.title,
                description=r.description,
                similarity_score=r.similarity_score,
                metadata=r.metadata
            )
            for r in results
        ]

        logger.info(
            f"User {current_user.get('user_id')} found {len(results)} "
            f"similar submissions to {submission_id}"
        )

        return SearchResponse(
            results=result_schemas,
            count=len(result_schemas),
            query=None,
            hackathon_id=hackathon_id
        )

    except ValueError as e:
        logger.warning(f"Invalid parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ZeroDBNotFound as e:
        logger.error(f"Submission not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {submission_id} not found or has no embedding"
        )
    except ZeroDBTimeoutError as e:
        logger.error(f"Search timeout: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Search request timed out. Please try again."
        )
    except ZeroDBError as e:
        logger.error(f"ZeroDB error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search"
        )
