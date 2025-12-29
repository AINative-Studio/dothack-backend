"""
Analytics Service

Provides statistics calculation and data export for hackathons.
Aggregates data from hackathon_participants, teams, submissions, and scores tables.
"""

import csv
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException
from fastapi import status as http_status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

# Configure logger
logger = logging.getLogger(__name__)

# Type for export formats
ExportFormat = Literal["json", "csv"]


async def get_hackathon_stats(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
) -> Dict[str, Any]:
    """
    Calculate statistics for a hackathon.

    Aggregates data from multiple tables to provide:
    - Total participants count (by role)
    - Total teams count
    - Total submissions count
    - Average scores per track (if tracks are defined in submissions)

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: UUID of the hackathon

    Returns:
        Dict with statistics:
        - total_participants: Total number of participants
        - participants_by_role: Dict of role -> count
        - total_teams: Number of teams
        - total_submissions: Number of submissions
        - average_scores: Dict of track -> average score
        - submissions_by_status: Dict of status -> count

    Raises:
        HTTPException: 404 if hackathon not found
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 500ms for typical hackathons

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> stats = await get_hackathon_stats(client, "hack-123")
        >>> print(f"Participants: {stats['total_participants']}")
        Participants: 42
    """
    try:
        logger.info(f"Calculating statistics for hackathon {hackathon_id}")

        # Step 1: Verify hackathon exists
        hackathons = await zerodb_client.tables.query_rows(
            "hackathons",
            filter={"hackathon_id": hackathon_id, "is_deleted": False},
        )

        if not hackathons or len(hackathons) == 0:
            logger.warning(f"Hackathon {hackathon_id} not found")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )

        # Step 2: Get participants
        logger.debug(f"Querying participants for hackathon {hackathon_id}")
        participants = await zerodb_client.tables.query_rows(
            "hackathon_participants",
            filter={"hackathon_id": hackathon_id},
        )

        total_participants = len(participants)

        # Count participants by role
        participants_by_role = {}
        for participant in participants:
            role = participant.get("role", "unknown")
            participants_by_role[role] = participants_by_role.get(role, 0) + 1

        # Step 3: Get teams
        logger.debug(f"Querying teams for hackathon {hackathon_id}")
        teams = await zerodb_client.tables.query_rows(
            "teams",
            filter={"hackathon_id": hackathon_id},
        )

        total_teams = len(teams)

        # Step 4: Get submissions
        logger.debug(f"Querying submissions for hackathon {hackathon_id}")
        submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter={"hackathon_id": hackathon_id},
        )

        total_submissions = len(submissions)

        # Count submissions by status
        submissions_by_status = {}
        for submission in submissions:
            status_val = submission.get("status", "unknown")
            submissions_by_status[status_val] = submissions_by_status.get(status_val, 0) + 1

        # Step 5: Calculate average scores per track
        logger.debug(f"Calculating average scores for hackathon {hackathon_id}")

        # Get all scores for this hackathon's submissions
        submission_ids = [s.get("submission_id") for s in submissions]

        average_scores = {}
        track_scores = {}  # track -> list of scores

        if submission_ids:
            # Query scores for all submissions
            all_scores = []
            for submission_id in submission_ids:
                scores = await zerodb_client.tables.query_rows(
                    "scores",
                    filter={"submission_id": submission_id},
                )
                all_scores.extend(scores)

            # Build submission_id -> track mapping
            submission_tracks = {}
            for submission in submissions:
                submission_id = submission.get("submission_id")
                track = submission.get("track", "general")
                submission_tracks[submission_id] = track

            # Group scores by track
            for score in all_scores:
                submission_id = score.get("submission_id")
                total_score = score.get("total_score", 0)

                track = submission_tracks.get(submission_id, "general")

                if track not in track_scores:
                    track_scores[track] = []
                track_scores[track].append(total_score)

            # Calculate averages
            for track, scores_list in track_scores.items():
                if scores_list:
                    average_scores[track] = sum(scores_list) / len(scores_list)

        logger.info(
            f"Statistics calculated for hackathon {hackathon_id}: "
            f"{total_participants} participants, {total_teams} teams, "
            f"{total_submissions} submissions"
        )

        return {
            "hackathon_id": hackathon_id,
            "total_participants": total_participants,
            "participants_by_role": participants_by_role,
            "total_teams": total_teams,
            "total_submissions": total_submissions,
            "submissions_by_status": submissions_by_status,
            "average_scores": average_scores,
            "calculated_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout calculating stats for hackathon {hackathon_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Statistics calculation timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error calculating stats for hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate statistics. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error calculating stats for hackathon {hackathon_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate statistics. Please contact support.",
        )


async def export_hackathon_data(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    format: ExportFormat = "json",
) -> Dict[str, Any]:
    """
    Export all hackathon data in JSON or CSV format.

    Retrieves and exports:
    - Hackathon details
    - All participants
    - All teams
    - All submissions
    - All scores

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: UUID of the hackathon
        format: Export format ("json" or "csv")

    Returns:
        Dict with export data:
        - format: Export format used
        - data: Exported data (structure varies by format)
            - JSON: Dict with nested hackathon, participants, teams, submissions, scores
            - CSV: String containing CSV data with all records

    Raises:
        HTTPException: 404 if hackathon not found
        HTTPException: 400 for invalid format
        HTTPException: 500 for database errors
        HTTPException: 504 for timeout errors

    Performance:
        Should complete in < 1000ms for typical hackathons

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> export = await export_hackathon_data(client, "hack-123", "json")
        >>> print(export['format'])
        json
        >>> print(len(export['data']['participants']))
        42
    """
    try:
        logger.info(f"Exporting hackathon {hackathon_id} data in {format} format")

        # Validate format
        if format not in ["json", "csv"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format '{format}'. Must be 'json' or 'csv'",
            )

        # Step 1: Get hackathon details
        hackathons = await zerodb_client.tables.query_rows(
            "hackathons",
            filter={"hackathon_id": hackathon_id, "is_deleted": False},
        )

        if not hackathons or len(hackathons) == 0:
            logger.warning(f"Hackathon {hackathon_id} not found for export")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )

        hackathon = hackathons[0]

        # Step 2: Get all related data
        logger.debug(f"Querying all data for hackathon {hackathon_id}")

        # Get participants
        participants = await zerodb_client.tables.query_rows(
            "hackathon_participants",
            filter={"hackathon_id": hackathon_id},
        )

        # Get teams
        teams = await zerodb_client.tables.query_rows(
            "teams",
            filter={"hackathon_id": hackathon_id},
        )

        # Get submissions
        submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter={"hackathon_id": hackathon_id},
        )

        # Get all scores for these submissions
        submission_ids = [s.get("submission_id") for s in submissions]
        all_scores = []

        if submission_ids:
            for submission_id in submission_ids:
                scores = await zerodb_client.tables.query_rows(
                    "scores",
                    filter={"submission_id": submission_id},
                )
                all_scores.extend(scores)

        logger.info(
            f"Retrieved data for export: {len(participants)} participants, "
            f"{len(teams)} teams, {len(submissions)} submissions, {len(all_scores)} scores"
        )

        # Step 3: Format data based on requested format
        if format == "json":
            export_data = {
                "hackathon": hackathon,
                "participants": participants,
                "teams": teams,
                "submissions": submissions,
                "scores": all_scores,
                "export_metadata": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "format": "json",
                    "record_counts": {
                        "participants": len(participants),
                        "teams": len(teams),
                        "submissions": len(submissions),
                        "scores": len(all_scores),
                    },
                },
            }

            return {
                "format": "json",
                "data": export_data,
            }

        elif format == "csv":
            # Create CSV with all data flattened
            output = io.StringIO()

            # Define CSV structure with flattened records
            fieldnames = [
                "record_type",
                "record_id",
                "hackathon_id",
                "hackathon_name",
                "user_id",
                "role",
                "team_id",
                "team_name",
                "submission_id",
                "project_name",
                "status",
                "score",
                "judge_id",
                "created_at",
            ]

            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            # Write hackathon info
            writer.writerow({
                "record_type": "hackathon",
                "record_id": hackathon.get("hackathon_id"),
                "hackathon_id": hackathon.get("hackathon_id"),
                "hackathon_name": hackathon.get("name"),
                "status": hackathon.get("status"),
                "created_at": hackathon.get("created_at"),
            })

            # Write participants
            for participant in participants:
                writer.writerow({
                    "record_type": "participant",
                    "record_id": participant.get("participant_id"),
                    "hackathon_id": participant.get("hackathon_id"),
                    "hackathon_name": hackathon.get("name"),
                    "user_id": participant.get("user_id"),
                    "role": participant.get("role"),
                    "status": participant.get("status"),
                    "created_at": participant.get("joined_at"),
                })

            # Write teams
            for team in teams:
                writer.writerow({
                    "record_type": "team",
                    "record_id": team.get("team_id"),
                    "hackathon_id": team.get("hackathon_id"),
                    "hackathon_name": hackathon.get("name"),
                    "team_id": team.get("team_id"),
                    "team_name": team.get("name"),
                    "created_at": team.get("created_at"),
                })

            # Write submissions
            for submission in submissions:
                writer.writerow({
                    "record_type": "submission",
                    "record_id": submission.get("submission_id"),
                    "hackathon_id": submission.get("hackathon_id"),
                    "hackathon_name": hackathon.get("name"),
                    "team_id": submission.get("team_id"),
                    "submission_id": submission.get("submission_id"),
                    "project_name": submission.get("project_name"),
                    "status": submission.get("status"),
                    "created_at": submission.get("created_at"),
                })

            # Write scores
            for score in all_scores:
                writer.writerow({
                    "record_type": "score",
                    "record_id": score.get("score_id"),
                    "hackathon_id": hackathon_id,
                    "hackathon_name": hackathon.get("name"),
                    "submission_id": score.get("submission_id"),
                    "judge_id": score.get("judge_participant_id"),
                    "score": score.get("total_score"),
                    "created_at": score.get("submitted_at"),
                })

            csv_data = output.getvalue()
            output.close()

            logger.info(f"Generated CSV export with {len(csv_data)} characters")

            return {
                "format": "csv",
                "data": csv_data,
            }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout exporting hackathon {hackathon_id} data: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Export timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(
            f"ZeroDB error exporting hackathon {hackathon_id} data: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export data. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error exporting hackathon {hackathon_id} data: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export data. Please contact support.",
        )
