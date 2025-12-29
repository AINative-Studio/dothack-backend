"""
Judging Service

Provides judging and scoring operations for hackathon submissions.
Includes score submission, retrieval, rankings calculation, and leaderboard generation.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)
from services.authorization import check_judge

# Configure logger
logger = logging.getLogger(__name__)


async def submit_score(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    judge_participant_id: str,
    hackathon_id: str,
    rubric_id: str,
    scores_breakdown: Dict[str, float],
    total_score: float,
    feedback: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit a score for a hackathon submission.

    This function handles the complete score submission workflow:
    1. Verifies the judge has JUDGE role for the hackathon
    2. Validates score data (non-negative, totals match, non-empty)
    3. Checks for duplicate scores from the same judge
    4. Inserts score into ZeroDB scores table

    Args:
        zerodb_client: ZeroDB client instance
        submission_id: UUID of the submission being scored
        judge_participant_id: UUID of the judge (participant_id)
        hackathon_id: UUID of the hackathon
        rubric_id: UUID of the rubric being used
        scores_breakdown: Dict of criterion -> score mappings
        total_score: Total score (must equal sum of scores_breakdown)
        feedback: Optional text feedback from judge

    Returns:
        Dict with score insertion result including row_ids

    Raises:
        HTTPException: 400 for validation errors
        HTTPException: 403 if user is not a judge
        HTTPException: 409 if judge already scored this submission
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 200ms for typical operations

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> result = await submit_score(
        ...     zerodb_client=client,
        ...     submission_id="sub-123",
        ...     judge_participant_id="judge-456",
        ...     hackathon_id="hack-789",
        ...     rubric_id="rubric-abc",
        ...     scores_breakdown={"innovation": 8, "technical": 9},
        ...     total_score=17.0,
        ...     feedback="Great work!"
        ... )
        >>> print(result)
        {'success': True, 'row_ids': ['score-xyz']}
    """
    try:
        # Step 1: Verify judge authorization
        logger.info(
            f"Verifying judge authorization for {judge_participant_id} "
            f"in hackathon {hackathon_id}"
        )
        await check_judge(
            zerodb_client=zerodb_client,
            user_id=judge_participant_id,
            hackathon_id=hackathon_id,
        )

        # Step 2: Validate score data
        logger.debug(f"Validating score data for submission {submission_id}")

        # Check for empty scores_breakdown
        if not scores_breakdown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scores_breakdown cannot be empty",
            )

        # Check for negative scores
        for criterion, score in scores_breakdown.items():
            if score < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Score for '{criterion}' cannot be negative: {score}",
                )

        # Validate total_score matches sum of breakdown
        calculated_total = sum(scores_breakdown.values())
        if abs(calculated_total - total_score) > 0.01:  # Allow small floating point differences
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"total_score ({total_score}) does not match sum of "
                    f"scores_breakdown ({calculated_total})"
                ),
            )

        # Step 3: Check for duplicate scores
        logger.debug(f"Checking for existing scores from judge {judge_participant_id}")
        existing_scores = await zerodb_client.tables.query_rows(
            "scores",
            filter={
                "submission_id": submission_id,
                "judge_participant_id": judge_participant_id,
            },
        )

        if existing_scores and len(existing_scores) > 0:
            logger.warning(
                f"Judge {judge_participant_id} already submitted score "
                f"for submission {submission_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Judge has already submitted a score for this submission",
            )

        # Step 4: Insert score
        score_id = str(uuid.uuid4())
        score_row = {
            "score_id": score_id,
            "submission_id": submission_id,
            "judge_participant_id": judge_participant_id,
            "rubric_id": rubric_id,
            "scores_breakdown": scores_breakdown,
            "total_score": total_score,
            "feedback": feedback,
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Inserting score {score_id} for submission {submission_id}")
        result = await zerodb_client.tables.insert_rows(
            "scores",
            rows=[score_row],
        )

        logger.info(
            f"Successfully submitted score {score_id} by judge {judge_participant_id} "
            f"for submission {submission_id}"
        )

        return {
            "success": True,
            "score_id": score_id,
            **result,
        }

    except HTTPException:
        # Re-raise HTTPException as-is
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout submitting score for submission {submission_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Score submission timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error submitting score for submission {submission_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit score. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error submitting score for submission {submission_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit score. Please contact support.",
        )


async def get_scores(
    zerodb_client: ZeroDBClient,
    submission_id: str,
    include_average: bool = False,
) -> Any:
    """
    Get all scores for a submission.

    Retrieves all judge scores for the specified submission from the scores table.
    Optionally calculates and includes the average score.

    Args:
        zerodb_client: ZeroDB client instance
        submission_id: UUID of the submission
        include_average: If True, returns dict with scores and average_score

    Returns:
        List of score objects, or dict with 'scores' and 'average_score' if include_average=True

    Raises:
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 100ms for typical queries

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> scores = await get_scores(client, "sub-123")
        >>> print(len(scores))
        3
        >>> scores_with_avg = await get_scores(client, "sub-123", include_average=True)
        >>> print(scores_with_avg['average_score'])
        24.5
    """
    try:
        logger.debug(f"Retrieving scores for submission {submission_id}")

        scores = await zerodb_client.tables.query_rows(
            "scores",
            filter={"submission_id": submission_id},
        )

        logger.info(f"Retrieved {len(scores)} scores for submission {submission_id}")

        if include_average:
            if scores and len(scores) > 0:
                total = sum(score["total_score"] for score in scores)
                average = total / len(scores)
            else:
                average = 0.0

            return {
                "scores": scores,
                "average_score": average,
            }

        return scores

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout retrieving scores for submission {submission_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error retrieving scores for submission {submission_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scores. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error retrieving scores for submission {submission_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scores. Please contact support.",
        )


async def calculate_rankings(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    track_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate final rankings for hackathon submissions.

    Computes rankings based on average scores from all judges. Rankings can be
    filtered by track. Submissions without any scores are excluded.

    Algorithm:
    1. Get all submissions for hackathon (optionally filtered by track)
    2. For each submission, calculate average score from all judges
    3. Sort by average score (descending)
    4. Assign ranks (1-based, with tie handling)

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: UUID of the hackathon
        track_id: Optional track UUID to filter rankings

    Returns:
        List of dicts with keys:
        - rank (int): 1-based ranking
        - submission_id (str): Submission UUID
        - project_id (str): Project UUID
        - average_score (float): Average score from all judges
        - score_count (int): Number of judge scores received

    Raises:
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 5s for 100 submissions

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> rankings = await calculate_rankings(client, "hack-123")
        >>> print(rankings[0])
        {
            'rank': 1,
            'submission_id': 'sub-456',
            'project_id': 'proj-789',
            'average_score': 28.5,
            'score_count': 4
        }
    """
    try:
        logger.info(f"Calculating rankings for hackathon {hackathon_id}")

        # Step 1: Get submissions (optionally filtered by track)
        if track_id:
            logger.debug(f"Filtering by track {track_id}")
            # First get projects in the track
            projects = await zerodb_client.tables.query_rows(
                "projects",
                filter={
                    "hackathon_id": hackathon_id,
                    "track_id": track_id,
                },
            )
            project_ids = [p["project_id"] for p in projects]

            # Then get submissions for those projects
            all_submissions = []
            for project_id in project_ids:
                subs = await zerodb_client.tables.query_rows(
                    "submissions",
                    filter={"project_id": project_id},
                )
                all_submissions.extend(subs)
        else:
            # Get all projects in hackathon, then their submissions
            projects = await zerodb_client.tables.query_rows(
                "projects",
                filter={"hackathon_id": hackathon_id},
            )
            project_ids = [p["project_id"] for p in projects]

            all_submissions = []
            for project_id in project_ids:
                subs = await zerodb_client.tables.query_rows(
                    "submissions",
                    filter={"project_id": project_id},
                )
                all_submissions.extend(subs)

        logger.info(f"Found {len(all_submissions)} submissions")

        # Step 2: Calculate average score for each submission
        rankings_data = []
        for submission in all_submissions:
            submission_id = submission["submission_id"]
            project_id = submission["project_id"]

            # Get all scores for this submission
            scores = await zerodb_client.tables.query_rows(
                "scores",
                filter={"submission_id": submission_id},
            )

            # Skip submissions with no scores
            if not scores or len(scores) == 0:
                logger.debug(f"Skipping submission {submission_id} - no scores")
                continue

            # Calculate average
            total = sum(score["total_score"] for score in scores)
            average_score = total / len(scores)

            rankings_data.append(
                {
                    "submission_id": submission_id,
                    "project_id": project_id,
                    "average_score": average_score,
                    "score_count": len(scores),
                }
            )

        # Step 3: Sort by average score (descending)
        rankings_data.sort(key=lambda x: x["average_score"], reverse=True)

        # Step 4: Assign ranks
        for idx, item in enumerate(rankings_data, start=1):
            item["rank"] = idx

        logger.info(
            f"Calculated rankings for {len(rankings_data)} scored submissions "
            f"in hackathon {hackathon_id}"
        )

        return rankings_data

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout calculating rankings for hackathon {hackathon_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Rankings calculation timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error calculating rankings for hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate rankings. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error calculating rankings for hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate rankings. Please contact support.",
        )


async def get_leaderboard(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    track_id: Optional[str] = None,
    top_n: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Get hackathon leaderboard with team and project details.

    Generates a formatted leaderboard by combining rankings with team and project
    information. This provides a complete view for displaying to participants.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: UUID of the hackathon
        track_id: Optional track UUID to filter leaderboard
        top_n: Optional limit to top N entries (e.g., top_n=10 for top 10)

    Returns:
        List of dicts with keys:
        - rank (int): 1-based ranking
        - submission_id (str): Submission UUID
        - project_id (str): Project UUID
        - project_name (str): Project name
        - team_id (str): Team UUID
        - team_name (str): Team name (or None if no team)
        - track_id (str): Track UUID (if track filtering used)
        - average_score (float): Average score
        - score_count (int): Number of scores

    Raises:
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 10s for 100 submissions with details

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> leaderboard = await get_leaderboard(client, "hack-123", top_n=10)
        >>> print(leaderboard[0])
        {
            'rank': 1,
            'team_name': 'Team Alpha',
            'project_name': 'AI Assistant',
            'average_score': 28.5,
            'score_count': 4
        }
    """
    try:
        logger.info(f"Generating leaderboard for hackathon {hackathon_id}")

        # Step 1: Get rankings
        rankings = await calculate_rankings(
            zerodb_client=zerodb_client,
            hackathon_id=hackathon_id,
            track_id=track_id,
        )

        # Step 2: Limit to top N if specified
        if top_n is not None:
            rankings = rankings[:top_n]
            logger.debug(f"Limited leaderboard to top {top_n} entries")

        # Step 3: Enrich with project and team details
        leaderboard = []
        for ranking in rankings:
            project_id = ranking["project_id"]

            # Get project details
            projects = await zerodb_client.tables.query_rows(
                "projects",
                filter={"project_id": project_id},
            )

            if not projects or len(projects) == 0:
                logger.warning(f"Project {project_id} not found, skipping")
                continue

            project = projects[0]
            project_name = project.get("name", "Unknown Project")
            team_id = project.get("team_id")

            # Get team details (if team exists)
            team_name = None
            if team_id:
                teams = await zerodb_client.tables.query_rows(
                    "teams",
                    filter={"team_id": team_id},
                )
                if teams and len(teams) > 0:
                    team_name = teams[0].get("name", "Unknown Team")
                else:
                    team_name = "N/A"
            else:
                team_name = "N/A"

            # Build leaderboard entry
            entry = {
                "rank": ranking["rank"],
                "submission_id": ranking["submission_id"],
                "project_id": project_id,
                "project_name": project_name,
                "team_id": team_id,
                "team_name": team_name,
                "average_score": ranking["average_score"],
                "score_count": ranking["score_count"],
            }

            if track_id:
                entry["track_id"] = track_id

            leaderboard.append(entry)

        logger.info(
            f"Generated leaderboard with {len(leaderboard)} entries "
            f"for hackathon {hackathon_id}"
        )

        return leaderboard

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout generating leaderboard for hackathon {hackathon_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Leaderboard generation timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error generating leaderboard for hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate leaderboard. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error generating leaderboard for hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate leaderboard. Please contact support.",
        )
