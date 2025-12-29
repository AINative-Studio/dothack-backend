"""
Hackathon API Routes

RESTful API endpoints for hackathon CRUD operations with authentication,
authorization, and comprehensive error handling.
"""

import logging
from typing import Any, Dict, Optional

from api.dependencies import get_current_user
from api.schemas.hackathon import (
    ErrorResponse,
    HackathonCreateRequest,
    HackathonDeleteResponse,
    HackathonListResponse,
    HackathonResponse,
    HackathonUpdateRequest,
)
from config import settings
from fastapi import APIRouter, Depends, HTTPException, Query, status
from integrations.zerodb.client import ZeroDBClient
from services import hackathon_service

# Configure logger
logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/api/v1/hackathons",
    tags=["Hackathons"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        504: {"model": ErrorResponse, "description": "Gateway Timeout"},
    },
)


def get_zerodb_client() -> ZeroDBClient:
    """
    Dependency to provide ZeroDB client instance.

    Returns:
        Configured ZeroDBClient instance

    Raises:
        HTTPException: 500 if ZeroDB credentials are not configured
    """
    try:
        return ZeroDBClient(
            api_key=settings.ZERODB_API_KEY,
            project_id=settings.ZERODB_PROJECT_ID,
            base_url=settings.ZERODB_BASE_URL,
        )
    except ValueError as e:
        logger.error(f"ZeroDB client configuration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database configuration error. Please contact support.",
        )


@router.post(
    "",
    response_model=HackathonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a hackathon",
    description="""
    Create a new hackathon with the authenticated user as ORGANIZER.

    The creator is automatically assigned the ORGANIZER role, granting them
    full permissions to manage the hackathon including updates, deletions,
    participant management, and judging configuration.

    **Authentication Required:** Yes (JWT or API Key)

    **Permissions:** Any authenticated user can create a hackathon

    **Request Body:**
    - name: Hackathon name (3-200 characters, required)
    - description: Detailed description (optional, max 5000 chars)
    - organizer_id: UUID of the organizer (must match authenticated user)
    - start_date: Start date/time in ISO 8601 format (required)
    - end_date: End date/time in ISO 8601 format (must be after start_date, required)
    - location: Physical location or "virtual" (required)
    - registration_deadline: Optional deadline in ISO 8601 (must be ≤ start_date)
    - max_participants: Optional participant limit (≥ 1)
    - website_url: Optional hackathon website URL
    - prizes: Optional prize information as JSON object
    - rules: Optional rules and guidelines text
    - status: Initial status (default: "draft")

    **Status Values:**
    - draft: Being planned, not visible to public
    - upcoming: Visible, accepting registrations
    - active: Currently running
    - judging: Submissions closed, judging in progress
    - completed: Finished, results published
    - cancelled: Cancelled

    **Response:** Created hackathon with hackathon_id

    **Error Responses:**
    - 400: Validation error (invalid dates, status, etc.)
    - 401: Not authenticated
    - 500: Database error
    - 504: Timeout
    """,
    responses={
        201: {
            "description": "Hackathon created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "hackathon_id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "AI Hackathon 2025",
                        "description": "Build AI-powered applications",
                        "organizer_id": "user-123",
                        "start_date": "2025-03-01T09:00:00Z",
                        "end_date": "2025-03-03T18:00:00Z",
                        "location": "San Francisco, CA",
                        "status": "draft",
                        "created_at": "2025-01-15T10:00:00Z",
                        "updated_at": "2025-01-15T10:00:00Z",
                    }
                }
            },
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Validation error",
                        "detail": "end_date must be after start_date",
                        "status_code": 400,
                    }
                }
            },
        },
    },
)
async def create_hackathon(
    request: HackathonCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> HackathonResponse:
    """
    Create a new hackathon endpoint.

    Validates request, creates hackathon, and adds creator as ORGANIZER.
    """
    logger.info(
        f"Create hackathon request from user {current_user.get('id')}: {request.name}"
    )

    # Ensure organizer_id matches authenticated user
    user_id = str(current_user.get("id"))
    if str(request.organizer_id) != user_id:
        logger.warning(
            f"User {user_id} attempted to create hackathon with different organizer_id: {request.organizer_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="organizer_id must match authenticated user",
        )

    hackathon = await hackathon_service.create_hackathon(
        zerodb_client=zerodb_client,
        name=request.name,
        description=request.description,
        organizer_id=user_id,
        start_date=request.start_date,
        end_date=request.end_date,
        location=request.location,
        registration_deadline=request.registration_deadline,
        max_participants=request.max_participants,
        website_url=str(request.website_url) if request.website_url else None,
        prizes=request.prizes,
        rules=request.rules,
        status=request.status.value,
    )

    logger.info(f"Hackathon created successfully: {hackathon['hackathon_id']}")
    return HackathonResponse(**hackathon)


@router.get(
    "",
    response_model=HackathonListResponse,
    summary="List hackathons",
    description="""
    List hackathons with pagination and optional status filtering.

    By default, returns active and upcoming hackathons. Soft-deleted
    hackathons are excluded.

    **Authentication Required:** Yes (JWT or API Key)

    **Permissions:** Any authenticated user can list hackathons

    **Query Parameters:**
    - skip: Number of records to skip (default: 0, for pagination)
    - limit: Maximum records to return (default: 100, max: 1000)
    - status: Optional status filter (draft, upcoming, active, judging, completed, cancelled)

    **Response:** Paginated list with total count

    **Error Responses:**
    - 400: Invalid pagination parameters
    - 401: Not authenticated
    - 500: Database error
    - 504: Timeout
    """,
    responses={
        200: {
            "description": "Hackathons retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "hackathons": [
                            {
                                "hackathon_id": "550e8400-e29b-41d4-a716-446655440000",
                                "name": "AI Hackathon 2025",
                                "description": "Build AI apps",
                                "start_date": "2025-03-01T09:00:00Z",
                                "end_date": "2025-03-03T18:00:00Z",
                                "status": "active",
                                "location": "San Francisco",
                            }
                        ],
                        "total": 1,
                        "skip": 0,
                        "limit": 100,
                    }
                }
            },
        }
    },
)
async def list_hackathons(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum records to return"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> HackathonListResponse:
    """
    List hackathons endpoint with pagination and filtering.
    """
    logger.info(
        f"List hackathons request from user {current_user.get('id')} "
        f"(skip={skip}, limit={limit}, status={status})"
    )

    result = await hackathon_service.list_hackathons(
        zerodb_client=zerodb_client,
        skip=skip,
        limit=limit,
        status_filter=status,
        include_deleted=False,
    )

    logger.info(f"Returning {len(result['hackathons'])} of {result['total']} hackathons")
    return HackathonListResponse(**result)


@router.get(
    "/{hackathon_id}",
    response_model=HackathonResponse,
    summary="Get hackathon details",
    description="""
    Retrieve detailed information about a specific hackathon.

    Returns all hackathon fields including organizer info, dates,
    participant counts, and current status.

    **Authentication Required:** Yes (JWT or API Key)

    **Permissions:** Any authenticated user can view hackathon details

    **Path Parameters:**
    - hackathon_id: UUID of the hackathon

    **Response:** Complete hackathon details

    **Error Responses:**
    - 401: Not authenticated
    - 404: Hackathon not found or deleted
    - 500: Database error
    - 504: Timeout
    """,
    responses={
        200: {
            "description": "Hackathon details retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "hackathon_id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "AI Hackathon 2025",
                        "description": "Build AI-powered applications",
                        "organizer_id": "user-123",
                        "start_date": "2025-03-01T09:00:00Z",
                        "end_date": "2025-03-03T18:00:00Z",
                        "location": "San Francisco, CA",
                        "max_participants": 100,
                        "website_url": "https://aihack2025.com",
                        "prizes": {"first": "$10,000", "second": "$5,000"},
                        "rules": "Standard hackathon rules apply",
                        "status": "active",
                        "created_at": "2025-01-15T10:00:00Z",
                        "updated_at": "2025-01-15T10:00:00Z",
                    }
                }
            },
        },
        404: {
            "description": "Hackathon not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Not found",
                        "detail": "Hackathon 550e8400-e29b-41d4-a716-446655440000 not found",
                        "status_code": 404,
                    }
                }
            },
        },
    },
)
async def get_hackathon(
    hackathon_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> HackathonResponse:
    """
    Get hackathon details endpoint.
    """
    logger.info(
        f"Get hackathon request from user {current_user.get('id')} for hackathon {hackathon_id}"
    )

    hackathon = await hackathon_service.get_hackathon(
        zerodb_client=zerodb_client,
        hackathon_id=hackathon_id,
        include_deleted=False,
    )

    logger.info(f"Returning hackathon details: {hackathon['name']}")
    return HackathonResponse(**hackathon)


@router.patch(
    "/{hackathon_id}",
    response_model=HackathonResponse,
    summary="Update hackathon",
    description="""
    Update hackathon details (ORGANIZER role required).

    Only users with the ORGANIZER role for this hackathon can make updates.
    All fields are optional - only provided fields will be updated.

    **Authentication Required:** Yes (JWT or API Key)

    **Permissions:** ORGANIZER role for this hackathon

    **Path Parameters:**
    - hackathon_id: UUID of the hackathon to update

    **Request Body:** (all fields optional)
    - name: Updated hackathon name (3-200 characters)
    - description: Updated description (max 5000 chars)
    - start_date: Updated start date in ISO 8601
    - end_date: Updated end date in ISO 8601
    - location: Updated location
    - registration_deadline: Updated deadline in ISO 8601
    - max_participants: Updated participant limit
    - website_url: Updated website URL
    - prizes: Updated prize information
    - rules: Updated rules
    - status: Updated status

    **Status Transitions:**
    Recommended flow: draft → upcoming → active → judging → completed

    **Response:** Updated hackathon details

    **Error Responses:**
    - 400: Validation error (invalid dates, status, etc.)
    - 401: Not authenticated
    - 403: User is not ORGANIZER for this hackathon
    - 404: Hackathon not found
    - 500: Database error
    - 504: Timeout
    """,
    responses={
        200: {
            "description": "Hackathon updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "hackathon_id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "AI Hackathon 2025 - Extended",
                        "status": "active",
                        "max_participants": 150,
                        "updated_at": "2025-01-20T15:30:00Z",
                    }
                }
            },
        },
        403: {
            "description": "Not authorized to update this hackathon",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Forbidden",
                        "detail": "User does not have ORGANIZER role for this hackathon",
                        "status_code": 403,
                    }
                }
            },
        },
    },
)
async def update_hackathon(
    hackathon_id: str,
    request: HackathonUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> HackathonResponse:
    """
    Update hackathon endpoint (ORGANIZER only).
    """
    user_id = str(current_user.get("id"))
    logger.info(
        f"Update hackathon request from user {user_id} for hackathon {hackathon_id}"
    )

    # Convert request to dict, excluding None values
    update_data = request.model_dump(exclude_none=True)

    if not update_data:
        logger.warning(f"Update request with no fields from user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    # Convert status enum to string if present
    if "status" in update_data:
        update_data["status"] = update_data["status"].value

    # Convert URLs to strings
    if "website_url" in update_data and update_data["website_url"]:
        update_data["website_url"] = str(update_data["website_url"])

    hackathon = await hackathon_service.update_hackathon(
        zerodb_client=zerodb_client,
        hackathon_id=hackathon_id,
        user_id=user_id,
        update_data=update_data,
    )

    logger.info(f"Hackathon {hackathon_id} updated successfully")
    return HackathonResponse(**hackathon)


@router.delete(
    "/{hackathon_id}",
    response_model=HackathonDeleteResponse,
    summary="Delete hackathon",
    description="""
    Soft delete a hackathon (ORGANIZER role required).

    This performs a soft delete, marking the hackathon as deleted
    (is_deleted=True) rather than removing the record. This preserves
    data integrity and allows for potential recovery.

    **Authentication Required:** Yes (JWT or API Key)

    **Permissions:** ORGANIZER role for this hackathon

    **Path Parameters:**
    - hackathon_id: UUID of the hackathon to delete

    **Response:** Deletion confirmation

    **Error Responses:**
    - 401: Not authenticated
    - 403: User is not ORGANIZER for this hackathon
    - 404: Hackathon not found or already deleted
    - 500: Database error
    - 504: Timeout

    **Note:** Soft-deleted hackathons will not appear in list endpoints
    or get requests by default. Contact support for recovery.
    """,
    responses={
        200: {
            "description": "Hackathon deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "hackathon_id": "550e8400-e29b-41d4-a716-446655440000",
                        "message": "Hackathon successfully deleted",
                    }
                }
            },
        },
        403: {
            "description": "Not authorized to delete this hackathon",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Forbidden",
                        "detail": "User does not have ORGANIZER role for this hackathon",
                        "status_code": 403,
                    }
                }
            },
        },
    },
)
async def delete_hackathon(
    hackathon_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> HackathonDeleteResponse:
    """
    Delete hackathon endpoint (ORGANIZER only, soft delete).
    """
    user_id = str(current_user.get("id"))
    logger.info(
        f"Delete hackathon request from user {user_id} for hackathon {hackathon_id}"
    )

    result = await hackathon_service.delete_hackathon(
        zerodb_client=zerodb_client,
        hackathon_id=hackathon_id,
        user_id=user_id,
    )

    logger.info(f"Hackathon {hackathon_id} deleted successfully")
    return HackathonDeleteResponse(**result)
