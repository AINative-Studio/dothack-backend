"""
Analytics API Routes

RESTful API endpoints for hackathon analytics and data export.
Provides statistics calculation and data export in multiple formats.
"""

import logging
from typing import Any, Dict, Literal

from api.dependencies import get_current_user
from config import settings
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from integrations.zerodb.client import ZeroDBClient
from pydantic import BaseModel, Field
from services import analytics_service
from services.authorization import check_organizer

# Configure logger
logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/api/v1/hackathons",
    tags=["Analytics"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - ORGANIZER role required"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
        504: {"description": "Gateway Timeout"},
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


# Response Models


class ParticipantsByRole(BaseModel):
    """Participants count by role"""

    organizer: int = Field(default=0, description="Number of organizers")
    judge: int = Field(default=0, description="Number of judges")
    builder: int = Field(default=0, description="Number of builders")


class SubmissionsByStatus(BaseModel):
    """Submissions count by status"""

    DRAFT: int = Field(default=0, description="Number of draft submissions")
    SUBMITTED: int = Field(default=0, description="Number of submitted submissions")
    SCORED: int = Field(default=0, description="Number of scored submissions")


class HackathonStatsResponse(BaseModel):
    """Response model for hackathon statistics"""

    hackathon_id: str = Field(..., description="Hackathon UUID")
    total_participants: int = Field(..., description="Total number of participants")
    participants_by_role: Dict[str, int] = Field(
        ..., description="Participants count by role"
    )
    total_teams: int = Field(..., description="Total number of teams")
    total_submissions: int = Field(..., description="Total number of submissions")
    submissions_by_status: Dict[str, int] = Field(
        ..., description="Submissions count by status"
    )
    average_scores: Dict[str, float] = Field(
        ..., description="Average scores per track"
    )
    calculated_at: str = Field(..., description="ISO 8601 timestamp of calculation")

    class Config:
        json_schema_extra = {
            "example": {
                "hackathon_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_participants": 42,
                "participants_by_role": {
                    "organizer": 2,
                    "judge": 5,
                    "builder": 35,
                },
                "total_teams": 8,
                "total_submissions": 8,
                "submissions_by_status": {
                    "DRAFT": 2,
                    "SUBMITTED": 3,
                    "SCORED": 3,
                },
                "average_scores": {
                    "general": 85.5,
                    "ai": 92.3,
                },
                "calculated_at": "2025-12-28T10:30:00Z",
            }
        }


class ExportMetadata(BaseModel):
    """Metadata about the export"""

    exported_at: str = Field(..., description="ISO 8601 timestamp of export")
    format: str = Field(..., description="Export format (json or csv)")
    record_counts: Dict[str, int] = Field(..., description="Count of each record type")


class HackathonExportResponse(BaseModel):
    """Response model for hackathon data export (JSON format)"""

    format: str = Field(..., description="Export format")
    data: Dict[str, Any] = Field(..., description="Exported data")

    class Config:
        json_schema_extra = {
            "example": {
                "format": "json",
                "data": {
                    "hackathon": {
                        "hackathon_id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "AI Hackathon 2025",
                        "status": "completed",
                    },
                    "participants": [
                        {
                            "participant_id": "part-123",
                            "user_id": "user-456",
                            "role": "builder",
                        }
                    ],
                    "teams": [{"team_id": "team-789", "name": "Team Awesome"}],
                    "submissions": [
                        {
                            "submission_id": "sub-abc",
                            "project_name": "Cool Project",
                        }
                    ],
                    "scores": [{"score_id": "score-xyz", "total_score": 95.0}],
                    "export_metadata": {
                        "exported_at": "2025-12-28T10:30:00Z",
                        "format": "json",
                        "record_counts": {
                            "participants": 42,
                            "teams": 8,
                            "submissions": 8,
                            "scores": 40,
                        },
                    },
                },
            }
        }


@router.get(
    "/{hackathon_id}/stats",
    response_model=HackathonStatsResponse,
    summary="Get hackathon statistics",
    description="""
    Calculate and return statistics for a hackathon (ORGANIZER only).

    Provides aggregated data including:
    - Total participant count with breakdown by role
    - Total team count
    - Total submission count with breakdown by status
    - Average scores per track

    **Authentication Required:** Yes (JWT or API Key)

    **Permissions:** ORGANIZER role for this hackathon

    **Path Parameters:**
    - hackathon_id: UUID of the hackathon

    **Response:** Statistics object with all aggregated data

    **Error Responses:**
    - 401: Not authenticated
    - 403: User is not ORGANIZER for this hackathon
    - 404: Hackathon not found
    - 500: Database error
    - 504: Timeout
    """,
    responses={
        200: {
            "description": "Statistics calculated successfully",
        },
        403: {
            "description": "Not authorized - ORGANIZER role required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Insufficient permissions. Required role: organizer"
                    }
                }
            },
        },
        404: {
            "description": "Hackathon not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Hackathon 550e8400-... not found"}
                }
            },
        },
    },
)
async def get_hackathon_stats(
    hackathon_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> HackathonStatsResponse:
    """
    Get hackathon statistics endpoint (ORGANIZER only).

    Verifies ORGANIZER role and returns aggregated statistics.
    """
    user_id = str(current_user.get("id"))
    logger.info(
        f"Statistics request from user {user_id} for hackathon {hackathon_id}"
    )

    # Check ORGANIZER authorization
    await check_organizer(
        zerodb_client=zerodb_client,
        user_id=user_id,
        hackathon_id=hackathon_id,
    )

    # Get statistics
    stats = await analytics_service.get_hackathon_stats(
        zerodb_client=zerodb_client,
        hackathon_id=hackathon_id,
    )

    logger.info(f"Statistics calculated for hackathon {hackathon_id}")
    return HackathonStatsResponse(**stats)


@router.get(
    "/{hackathon_id}/export",
    summary="Export hackathon data",
    description="""
    Export all hackathon data in JSON or CSV format (ORGANIZER only).

    Exports complete hackathon data including:
    - Hackathon details
    - All participants
    - All teams
    - All submissions
    - All scores

    **Authentication Required:** Yes (JWT or API Key)

    **Permissions:** ORGANIZER role for this hackathon

    **Path Parameters:**
    - hackathon_id: UUID of the hackathon

    **Query Parameters:**
    - format: Export format - "json" (default) or "csv"

    **Response Formats:**
    - JSON: Structured JSON with nested objects (application/json)
    - CSV: Flattened CSV with all records (text/csv)

    **Error Responses:**
    - 400: Invalid format parameter
    - 401: Not authenticated
    - 403: User is not ORGANIZER for this hackathon
    - 404: Hackathon not found
    - 500: Database error
    - 504: Timeout
    """,
    responses={
        200: {
            "description": "Data exported successfully",
            "content": {
                "application/json": {
                    "example": {
                        "format": "json",
                        "data": {
                            "hackathon": {"hackathon_id": "...", "name": "..."},
                            "participants": [],
                            "teams": [],
                            "submissions": [],
                            "scores": [],
                        },
                    }
                },
                "text/csv": {
                    "example": "record_type,record_id,hackathon_id,...\nhackathon,hack-123,...\n"
                },
            },
        },
        400: {
            "description": "Invalid format parameter",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid format 'xml'. Must be 'json' or 'csv'"
                    }
                }
            },
        },
        403: {
            "description": "Not authorized - ORGANIZER role required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Insufficient permissions. Required role: organizer"
                    }
                }
            },
        },
    },
)
async def export_hackathon_data(
    hackathon_id: str,
    format: Literal["json", "csv"] = Query(
        default="json", description="Export format (json or csv)"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Response:
    """
    Export hackathon data endpoint (ORGANIZER only).

    Verifies ORGANIZER role and exports all hackathon data in requested format.
    Returns different content types based on format parameter.
    """
    user_id = str(current_user.get("id"))
    logger.info(
        f"Export request from user {user_id} for hackathon {hackathon_id} "
        f"in {format} format"
    )

    # Check ORGANIZER authorization
    await check_organizer(
        zerodb_client=zerodb_client,
        user_id=user_id,
        hackathon_id=hackathon_id,
    )

    # Export data
    export_result = await analytics_service.export_hackathon_data(
        zerodb_client=zerodb_client,
        hackathon_id=hackathon_id,
        format=format,
    )

    logger.info(f"Data exported for hackathon {hackathon_id} in {format} format")

    # Return response based on format
    if format == "csv":
        # Return CSV as text/csv
        return Response(
            content=export_result["data"],
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=hackathon_{hackathon_id}_export.csv"
            },
        )
    else:
        # Return JSON (FastAPI will handle serialization)
        return HackathonExportResponse(**export_result)
