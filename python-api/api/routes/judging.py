"""
Judging API Routes

Provides endpoints for:
- Score submission by judges
- Hackathon results and leaderboards
- Judge assignment queries

All endpoints require authentication. Score submission requires JUDGE role.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from api.dependencies import get_current_user
from api.schemas.judging import (
    ErrorResponse,
    LeaderboardResponse,
    RankingsResponse,
    ScoreSubmitRequest,
    ScoreResponse,
)
from config import settings
from fastapi import APIRouter, Depends, HTTPException, Query, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.judging_service import (
    calculate_rankings,
    get_leaderboard,
    get_scores,
    submit_score,
)

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(
    prefix="/judging",
    tags=["Judging"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Resource not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Gateway timeout"},
    },
)


def get_zerodb_client() -> ZeroDBClient:
    """
    Dependency to create ZeroDB client instance.

    Returns:
        Configured ZeroDB client with API key and project ID from settings

    Raises:
        HTTPException: 500 if ZeroDB credentials are missing
    """
    if not settings.ZERODB_API_KEY or not settings.ZERODB_PROJECT_ID:
        logger.error("ZeroDB credentials not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database configuration error. Please contact support.",
        )

    return ZeroDBClient(
        api_key=settings.ZERODB_API_KEY,
        project_id=settings.ZERODB_PROJECT_ID,
        base_url=settings.ZERODB_BASE_URL,
    )


@router.post(
    "/scores",
    status_code=status.HTTP_201_CREATED,
    response_model=Dict[str, Any],
    summary="Submit score for submission",
    description=(
        "Submit a judge's score for a hackathon submission. "
        "Requires JUDGE role for the hackathon. "
        "Judge can only submit one score per submission."
    ),
)
async def submit_score_endpoint(
    submission_id: str = Query(..., description="UUID of submission to score"),
    hackathon_id: str = Query(..., description="UUID of hackathon"),
    rubric_id: str = Query(..., description="UUID of judging rubric"),
    score_request: ScoreSubmitRequest = ...,
    user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Submit a score for a hackathon submission.

    **Judge-only endpoint** - User must have JUDGE role for the hackathon.

    The request body should contain:
    - judge_id: UUID of the judge (should match authenticated user)
    - criteria: Name of judging criteria
    - score: Score value (0-100)
    - comment: Optional feedback comment

    **Validation:**
    - Judge must have JUDGE role for hackathon
    - Judge cannot submit duplicate scores for same submission
    - Score must be between 0 and 100
    - Total score must match sum of criteria scores

    Args:
        submission_id: UUID of submission being scored
        hackathon_id: UUID of hackathon
        rubric_id: UUID of judging rubric
        score_request: Score submission data
        user: Authenticated user from JWT token
        zerodb_client: ZeroDB client instance

    Returns:
        Success response with score_id and metadata

    Raises:
        HTTPException:
            - 400: Invalid score data
            - 401: Not authenticated
            - 403: Not a judge for this hackathon
            - 409: Judge already scored this submission
            - 500: Database error
            - 504: Request timeout

    Example Response:
        ```json
        {
            "success": true,
            "score_id": "550e8400-e29b-41d4-a716-446655440000",
            "row_ids": ["score-123"]
        }
        ```
    """
    try:
        logger.info(
            f"Score submission request: submission={submission_id}, "
            f"judge={score_request.judge_id}, hackathon={hackathon_id}"
        )

        # Verify judge_id matches authenticated user
        if str(score_request.judge_id) != user.get("id"):
            logger.warning(
                f"Judge ID mismatch: token={user.get('id')}, request={score_request.judge_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Judge ID in request must match authenticated user",
            )

        # Convert single criterion score to breakdown format
        scores_breakdown = {score_request.criteria: score_request.score}
        total_score = score_request.score

        # Submit score via service
        result = await submit_score(
            zerodb_client=zerodb_client,
            submission_id=submission_id,
            judge_participant_id=str(score_request.judge_id),
            hackathon_id=hackathon_id,
            rubric_id=rubric_id,
            scores_breakdown=scores_breakdown,
            total_score=total_score,
            feedback=score_request.comment,
        )

        logger.info(f"Score submitted successfully: {result.get('score_id')}")

        return result

    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise

    except Exception as e:
        logger.error(f"Unexpected error in submit_score_endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit score. Please contact support.",
        )


@router.get(
    "/hackathons/{hackathon_id}/results",
    status_code=status.HTTP_200_OK,
    response_model=LeaderboardResponse,
    summary="Get hackathon results",
    description=(
        "Get final results and leaderboard for a hackathon. "
        "Shows rankings based on average scores from all judges. "
        "Optionally filter by track."
    ),
)
async def get_hackathon_results(
    hackathon_id: str,
    track_id: Optional[str] = Query(None, description="Optional track UUID to filter results"),
    top_n: Optional[int] = Query(
        None,
        ge=1,
        le=1000,
        description="Limit to top N entries (max 1000)",
    ),
    user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> LeaderboardResponse:
    """
    Get hackathon results and leaderboard.

    Retrieves final rankings with team and project details. Results are calculated
    based on average scores from all judges. Submissions without scores are excluded.

    **Query Parameters:**
    - track_id (optional): Filter by specific track
    - top_n (optional): Limit results to top N entries (1-1000)

    **Response includes:**
    - Rank (1-based)
    - Team name and project title
    - Average score across all judges
    - Number of scores received

    Args:
        hackathon_id: UUID of hackathon
        track_id: Optional track UUID filter
        top_n: Optional limit on number of results
        user: Authenticated user
        zerodb_client: ZeroDB client instance

    Returns:
        LeaderboardResponse with hackathon details and ranked entries

    Raises:
        HTTPException:
            - 401: Not authenticated
            - 404: Hackathon not found
            - 500: Database error
            - 504: Request timeout

    Example Response:
        ```json
        {
            "hackathon_id": "hack-123",
            "hackathon_name": "AI Hackathon 2024",
            "entries": [
                {
                    "rank": 1,
                    "submission_id": "sub-456",
                    "project_id": "proj-789",
                    "project_name": "AI Assistant",
                    "team_id": "team-abc",
                    "team_name": "Team Alpha",
                    "average_score": 28.5,
                    "score_count": 4
                }
            ],
            "total_entries": 10,
            "last_updated": "2024-01-01T00:00:00"
        }
        ```
    """
    try:
        logger.info(f"Fetching results for hackathon {hackathon_id}, track={track_id}, top_n={top_n}")

        # Get leaderboard from service
        leaderboard_entries = await get_leaderboard(
            zerodb_client=zerodb_client,
            hackathon_id=hackathon_id,
            track_id=track_id,
            top_n=top_n,
        )

        # Get hackathon details
        hackathons = await zerodb_client.tables.query_rows(
            "hackathons",
            filter={"hackathon_id": hackathon_id},
        )

        if not hackathons or len(hackathons) == 0:
            logger.warning(f"Hackathon not found: {hackathon_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )

        hackathon = hackathons[0]
        hackathon_name = hackathon.get("name", "Unknown Hackathon")

        # Build response
        response = LeaderboardResponse(
            hackathon_id=UUID(hackathon_id),
            hackathon_name=hackathon_name,
            entries=[
                {
                    "rank": entry["rank"],
                    "submission_id": UUID(entry["submission_id"]),
                    "team_name": entry["team_name"],
                    "project_title": entry["project_name"],
                    "total_score": entry["average_score"],  # Note: using average as total
                    "average_score": entry["average_score"],
                    "score_count": entry["score_count"],
                    "created_at": entry.get("created_at", "2024-01-01T00:00:00"),
                }
                for entry in leaderboard_entries
            ],
            total_entries=len(leaderboard_entries),
            last_updated=None,  # TODO: Add last_updated tracking
        )

        logger.info(f"Retrieved {len(leaderboard_entries)} results for hackathon {hackathon_id}")

        return response

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout fetching results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"ZeroDB error fetching results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch results. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error in get_hackathon_results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch results. Please contact support.",
        )


@router.get(
    "/assignments",
    status_code=status.HTTP_200_OK,
    response_model=List[Dict[str, Any]],
    summary="Get judge assignments",
    description=(
        "Get list of submissions assigned to the authenticated judge. "
        "Requires JUDGE role. Returns submissions the judge needs to score."
    ),
)
async def get_judge_assignments(
    hackathon_id: str = Query(..., description="UUID of hackathon"),
    user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> List[Dict[str, Any]]:
    """
    Get submissions assigned to judge.

    Returns list of submissions that the authenticated user (as a judge) is
    assigned to score for the specified hackathon.

    **Response includes:**
    - Submission ID and project details
    - Team information
    - Submission status
    - Whether judge has already scored

    Args:
        hackathon_id: UUID of hackathon
        user: Authenticated user (must be judge)
        zerodb_client: ZeroDB client instance

    Returns:
        List of submission assignments with project and team details

    Raises:
        HTTPException:
            - 401: Not authenticated
            - 403: Not a judge for this hackathon
            - 500: Database error
            - 504: Request timeout

    Example Response:
        ```json
        [
            {
                "submission_id": "sub-123",
                "project_id": "proj-456",
                "project_name": "AI Tool",
                "team_id": "team-789",
                "team_name": "Team Beta",
                "already_scored": false,
                "submission_url": "https://example.com/project",
                "created_at": "2024-01-01T00:00:00"
            }
        ]
        ```
    """
    try:
        logger.info(f"Fetching assignments for judge {user.get('id')} in hackathon {hackathon_id}")

        # Verify user is a judge for this hackathon
        judge_id = user.get("id")
        participants = await zerodb_client.tables.query_rows(
            "hackathon_participants",
            filter={
                "user_id": judge_id,
                "hackathon_id": hackathon_id,
            },
        )

        if not participants or len(participants) == 0:
            logger.warning(f"User {judge_id} is not a participant in hackathon {hackathon_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a participant in this hackathon",
            )

        participant = participants[0]
        if participant.get("role") != "judge":
            logger.warning(f"User {judge_id} is not a judge in hackathon {hackathon_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a judge for this hackathon",
            )

        # Get all projects for this hackathon
        projects = await zerodb_client.tables.query_rows(
            "projects",
            filter={"hackathon_id": hackathon_id},
        )

        logger.info(f"Found {len(projects)} projects in hackathon {hackathon_id}")

        # For each project, get submissions and check if judge has scored
        assignments = []
        for project in projects:
            project_id = project["project_id"]

            # Get submissions for this project
            submissions = await zerodb_client.tables.query_rows(
                "submissions",
                filter={"project_id": project_id},
            )

            for submission in submissions:
                submission_id = submission["submission_id"]

                # Check if judge has already scored this submission
                existing_scores = await zerodb_client.tables.query_rows(
                    "scores",
                    filter={
                        "submission_id": submission_id,
                        "judge_participant_id": judge_id,
                    },
                )

                already_scored = len(existing_scores) > 0

                # Get team details if team exists
                team_id = project.get("team_id")
                team_name = "N/A"
                if team_id:
                    teams = await zerodb_client.tables.query_rows(
                        "teams",
                        filter={"team_id": team_id},
                    )
                    if teams and len(teams) > 0:
                        team_name = teams[0].get("name", "Unknown Team")

                # Build assignment entry
                assignment = {
                    "submission_id": submission_id,
                    "project_id": project_id,
                    "project_name": project.get("name", "Unknown Project"),
                    "team_id": team_id,
                    "team_name": team_name,
                    "already_scored": already_scored,
                    "submission_url": submission.get("url"),
                    "created_at": submission.get("created_at"),
                }

                assignments.append(assignment)

        logger.info(f"Retrieved {len(assignments)} assignments for judge {judge_id}")

        return assignments

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout fetching assignments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"ZeroDB error fetching assignments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch assignments. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error in get_judge_assignments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch assignments. Please contact support.",
        )
