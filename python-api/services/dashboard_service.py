"""
Dashboard Service

Business logic for dashboard aggregation endpoints.
Provides efficient data aggregation for role-based dashboard views.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

logger = logging.getLogger(__name__)


async def get_organizer_dashboard(
    zerodb_client: ZeroDBClient, user_id: str
) -> Dict[str, Any]:
    """
    Get dashboard data for organizer role.

    Aggregates:
    - Hackathons organized by user
    - Total participants, teams, submissions across all hackathons
    - Pending judgments count

    Args:
        zerodb_client: ZeroDB client instance
        user_id: User ID of the organizer

    Returns:
        Dictionary with organizer dashboard data

    Raises:
        HTTPException: 500 if database error, 504 if timeout
    """
    try:
        logger.info(f"Fetching organizer dashboard for user {user_id}")

        # Get hackathons organized by user
        my_hackathons = await zerodb_client.tables.query_rows(
            "hackathons",
            filter={"organizer_id": user_id, "is_deleted": False},
            limit=1000,
        )

        logger.info(f"Found {len(my_hackathons)} hackathons for organizer {user_id}")

        # Aggregate stats across all hackathons
        total_participants = 0
        total_teams = 0
        total_submissions = 0
        pending_judgments = 0

        hackathon_summaries = []

        for hackathon in my_hackathons:
            hackathon_id = hackathon["hackathon_id"]

            # Get participant count
            participants = await zerodb_client.tables.query_rows(
                "hackathon_participants",
                filter={"hackathon_id": hackathon_id},
                limit=10000,
            )
            participant_count = len(participants)
            total_participants += participant_count

            # Get team count
            teams = await zerodb_client.tables.query_rows(
                "teams", filter={"hackathon_id": hackathon_id}, limit=10000
            )
            team_count = len(teams)
            total_teams += team_count

            # Get submission count (projects with submissions)
            submissions = await zerodb_client.tables.query_rows(
                "submissions",
                filter={"hackathon_id": hackathon_id},
                limit=10000,
            )
            submission_count = len(submissions)
            total_submissions += submission_count

            # Count pending judgments (submissions without enough scores)
            for submission in submissions:
                submission_id = submission["submission_id"]
                scores = await zerodb_client.tables.query_rows(
                    "scores",
                    filter={"submission_id": submission_id},
                    limit=100,
                )
                # If no scores, it's pending
                if len(scores) == 0:
                    pending_judgments += 1

            # Build hackathon summary
            hackathon_summaries.append(
                {
                    "hackathon_id": hackathon_id,
                    "name": hackathon.get("name"),
                    "status": hackathon.get("status"),
                    "start_date": hackathon.get("start_date"),
                    "end_date": hackathon.get("end_date"),
                    "participant_count": participant_count,
                    "team_count": team_count,
                    "submission_count": submission_count,
                }
            )

        logger.info(
            f"Organizer dashboard: {len(hackathon_summaries)} hackathons, "
            f"{total_participants} participants, {total_teams} teams, "
            f"{total_submissions} submissions, {pending_judgments} pending judgments"
        )

        return {
            "my_hackathons": hackathon_summaries,
            "total_participants": total_participants,
            "total_teams": total_teams,
            "total_submissions": total_submissions,
            "pending_judgments": pending_judgments,
        }

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout fetching organizer dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error fetching organizer dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error in get_organizer_dashboard: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data. Please contact support.",
        )


async def get_builder_dashboard(
    zerodb_client: ZeroDBClient, user_id: str
) -> Dict[str, Any]:
    """
    Get dashboard data for builder role.

    Aggregates:
    - Hackathons user has joined
    - Teams user is part of
    - Submissions user has made
    - Upcoming deadlines

    Args:
        zerodb_client: ZeroDB client instance
        user_id: User ID of the builder

    Returns:
        Dictionary with builder dashboard data

    Raises:
        HTTPException: 500 if database error, 504 if timeout
    """
    try:
        logger.info(f"Fetching builder dashboard for user {user_id}")

        # Get hackathons user has joined as builder
        participations = await zerodb_client.tables.query_rows(
            "hackathon_participants",
            filter={"user_id": user_id, "role": "builder"},
            limit=1000,
        )

        logger.info(f"Found {len(participations)} participations for builder {user_id}")

        registered_hackathons = []
        upcoming_deadlines = []

        for participation in participations:
            hackathon_id = participation["hackathon_id"]

            # Get hackathon details
            hackathons = await zerodb_client.tables.query_rows(
                "hackathons",
                filter={"hackathon_id": hackathon_id, "is_deleted": False},
                limit=1,
            )

            if not hackathons:
                continue

            hackathon = hackathons[0]

            registered_hackathons.append(
                {
                    "hackathon_id": hackathon_id,
                    "name": hackathon.get("name"),
                    "status": hackathon.get("status"),
                    "start_date": hackathon.get("start_date"),
                    "end_date": hackathon.get("end_date"),
                    "registration_deadline": hackathon.get("registration_deadline"),
                    "location": hackathon.get("location"),
                    "my_role": participation.get("role", "builder"),
                }
            )

            # Add upcoming deadlines
            now = datetime.utcnow()

            # Registration deadline
            if hackathon.get("registration_deadline"):
                reg_deadline = datetime.fromisoformat(
                    hackathon["registration_deadline"].replace("Z", "+00:00")
                )
                if reg_deadline > now:
                    days_remaining = (reg_deadline - now).days
                    upcoming_deadlines.append(
                        {
                            "hackathon_id": hackathon_id,
                            "hackathon_name": hackathon.get("name"),
                            "deadline_type": "registration",
                            "deadline": hackathon["registration_deadline"],
                            "days_remaining": days_remaining,
                        }
                    )

            # Submission deadline (end_date)
            if hackathon.get("end_date"):
                end_date = datetime.fromisoformat(
                    hackathon["end_date"].replace("Z", "+00:00")
                )
                if end_date > now:
                    days_remaining = (end_date - now).days
                    upcoming_deadlines.append(
                        {
                            "hackathon_id": hackathon_id,
                            "hackathon_name": hackathon.get("name"),
                            "deadline_type": "submission",
                            "deadline": hackathon["end_date"],
                            "days_remaining": days_remaining,
                        }
                    )

        # Sort deadlines by date
        upcoming_deadlines.sort(key=lambda x: x["deadline"])

        # Get user's teams
        team_memberships = await zerodb_client.tables.query_rows(
            "team_members",
            filter={"user_id": user_id},
            limit=1000,
        )

        my_teams = []

        for membership in team_memberships:
            team_id = membership["team_id"]

            # Get team details
            teams = await zerodb_client.tables.query_rows(
                "teams", filter={"team_id": team_id}, limit=1
            )

            if not teams:
                continue

            team = teams[0]
            hackathon_id = team.get("hackathon_id")

            # Get hackathon name
            hackathons = await zerodb_client.tables.query_rows(
                "hackathons", filter={"hackathon_id": hackathon_id}, limit=1
            )

            hackathon_name = (
                hackathons[0].get("name") if hackathons else "Unknown Hackathon"
            )

            # Count team members
            members = await zerodb_client.tables.query_rows(
                "team_members", filter={"team_id": team_id}, limit=100
            )

            my_teams.append(
                {
                    "team_id": team_id,
                    "name": team.get("name"),
                    "hackathon_id": hackathon_id,
                    "hackathon_name": hackathon_name,
                    "status": team.get("status"),
                    "member_count": len(members),
                    "my_role": membership.get("role", "MEMBER"),
                }
            )

        # Get user's submissions (through teams)
        my_submissions = []

        for team in my_teams:
            team_id = team["team_id"]

            # Get projects for this team
            projects = await zerodb_client.tables.query_rows(
                "projects", filter={"team_id": team_id}, limit=100
            )

            for project in projects:
                project_id = project["project_id"]

                # Get submissions for this project
                submissions = await zerodb_client.tables.query_rows(
                    "submissions", filter={"project_id": project_id}, limit=100
                )

                for submission in submissions:
                    my_submissions.append(
                        {
                            "submission_id": submission["submission_id"],
                            "project_id": project_id,
                            "project_name": project.get("name"),
                            "team_id": team_id,
                            "team_name": team["name"],
                            "hackathon_id": team["hackathon_id"],
                            "hackathon_name": team["hackathon_name"],
                            "submitted_at": submission.get("submitted_at"),
                            "status": submission.get("status", "submitted"),
                        }
                    )

        logger.info(
            f"Builder dashboard: {len(registered_hackathons)} hackathons, "
            f"{len(my_teams)} teams, {len(my_submissions)} submissions, "
            f"{len(upcoming_deadlines)} upcoming deadlines"
        )

        return {
            "registered_hackathons": registered_hackathons,
            "my_teams": my_teams,
            "my_submissions": my_submissions,
            "upcoming_deadlines": upcoming_deadlines[:10],  # Limit to 10 most urgent
        }

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout fetching builder dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error fetching builder dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error in get_builder_dashboard: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data. Please contact support.",
        )


async def get_judge_dashboard(
    zerodb_client: ZeroDBClient, user_id: str
) -> Dict[str, Any]:
    """
    Get dashboard data for judge role.

    Aggregates:
    - Hackathons where user is a judge
    - Submissions assigned to judge
    - Completed judgments count
    - Pending submissions

    Args:
        zerodb_client: ZeroDB client instance
        user_id: User ID of the judge

    Returns:
        Dictionary with judge dashboard data

    Raises:
        HTTPException: 500 if database error, 504 if timeout
    """
    try:
        logger.info(f"Fetching judge dashboard for user {user_id}")

        # Get hackathons where user is a judge
        participations = await zerodb_client.tables.query_rows(
            "hackathon_participants",
            filter={"user_id": user_id, "role": "judge"},
            limit=1000,
        )

        logger.info(f"Found {len(participations)} judge assignments for user {user_id}")

        assigned_hackathons = []
        total_submissions_to_judge = 0
        total_completed_judgments = 0
        pending_submissions = []

        for participation in participations:
            hackathon_id = participation["hackathon_id"]

            # Get hackathon details
            hackathons = await zerodb_client.tables.query_rows(
                "hackathons",
                filter={"hackathon_id": hackathon_id, "is_deleted": False},
                limit=1,
            )

            if not hackathons:
                continue

            hackathon = hackathons[0]

            # Get all submissions for this hackathon
            submissions = await zerodb_client.tables.query_rows(
                "submissions",
                filter={"hackathon_id": hackathon_id},
                limit=10000,
            )

            assigned_count = len(submissions)
            completed_count = 0

            # Check which submissions this judge has scored
            for submission in submissions:
                submission_id = submission["submission_id"]

                # Check if judge has scored this submission
                scores = await zerodb_client.tables.query_rows(
                    "scores",
                    filter={"submission_id": submission_id, "judge_participant_id": user_id},
                    limit=1,
                )

                if scores:
                    completed_count += 1
                else:
                    # Add to pending list
                    project_id = submission.get("project_id")

                    # Get project details
                    projects = await zerodb_client.tables.query_rows(
                        "projects", filter={"project_id": project_id}, limit=1
                    )

                    project_name = (
                        projects[0].get("name") if projects else "Unknown Project"
                    )
                    team_id = projects[0].get("team_id") if projects else None

                    # Get team details
                    team_name = "Unknown Team"
                    if team_id:
                        teams = await zerodb_client.tables.query_rows(
                            "teams", filter={"team_id": team_id}, limit=1
                        )
                        if teams:
                            team_name = teams[0].get("name", "Unknown Team")

                    pending_submissions.append(
                        {
                            "submission_id": submission_id,
                            "project_id": project_id,
                            "project_name": project_name,
                            "team_id": team_id,
                            "team_name": team_name,
                            "hackathon_id": hackathon_id,
                            "hackathon_name": hackathon.get("name"),
                            "submitted_at": submission.get("submitted_at"),
                            "track_id": (
                                projects[0].get("track_id") if projects else None
                            ),
                        }
                    )

            total_submissions_to_judge += assigned_count
            total_completed_judgments += completed_count

            assigned_hackathons.append(
                {
                    "hackathon_id": hackathon_id,
                    "name": hackathon.get("name"),
                    "status": hackathon.get("status"),
                    "start_date": hackathon.get("start_date"),
                    "end_date": hackathon.get("end_date"),
                    "assigned_submissions": assigned_count,
                    "completed_judgments": completed_count,
                }
            )

        # Sort pending submissions by submission date
        pending_submissions.sort(key=lambda x: x.get("submitted_at", ""))

        logger.info(
            f"Judge dashboard: {len(assigned_hackathons)} hackathons, "
            f"{total_submissions_to_judge} assigned, "
            f"{total_completed_judgments} completed, "
            f"{len(pending_submissions)} pending"
        )

        return {
            "assigned_hackathons": assigned_hackathons,
            "submissions_to_judge": total_submissions_to_judge,
            "completed_judgments": total_completed_judgments,
            "pending_submissions": pending_submissions[:20],  # Limit to 20 most recent
        }

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout fetching judge dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error fetching judge dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error in get_judge_dashboard: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data. Please contact support.",
        )


async def get_hackathon_overview(
    zerodb_client: ZeroDBClient, hackathon_id: str, user_id: str
) -> Dict[str, Any]:
    """
    Get hackathon overview dashboard with stats and recent activity.

    Requires ORGANIZER role or ADMIN access.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: Hackathon ID
        user_id: User ID requesting overview (for authorization)

    Returns:
        Dictionary with hackathon overview data

    Raises:
        HTTPException: 403 if not authorized, 404 if not found, 500 if error, 504 if timeout
    """
    try:
        logger.info(
            f"Fetching hackathon overview for {hackathon_id} by user {user_id}"
        )

        # Get hackathon details
        hackathons = await zerodb_client.tables.query_rows(
            "hackathons",
            filter={"hackathon_id": hackathon_id, "is_deleted": False},
            limit=1,
        )

        if not hackathons:
            logger.warning(f"Hackathon {hackathon_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found",
            )

        hackathon = hackathons[0]

        # Check authorization (must be organizer)
        if hackathon.get("organizer_id") != user_id:
            # Check if user is ADMIN (future implementation)
            logger.warning(
                f"User {user_id} not authorized to view overview for hackathon {hackathon_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organizers can view hackathon overview",
            )

        # Get participants
        participants = await zerodb_client.tables.query_rows(
            "hackathon_participants",
            filter={"hackathon_id": hackathon_id},
            limit=10000,
        )

        participant_count = len(participants)
        builder_count = sum(1 for p in participants if p.get("role") == "builder")
        judge_count = sum(1 for p in participants if p.get("role") == "judge")

        # Get teams
        teams = await zerodb_client.tables.query_rows(
            "teams", filter={"hackathon_id": hackathon_id}, limit=10000
        )
        team_count = len(teams)

        # Get submissions
        submissions = await zerodb_client.tables.query_rows(
            "submissions",
            filter={"hackathon_id": hackathon_id},
            limit=10000,
        )
        submission_count = len(submissions)

        # Track distribution (count submissions by track)
        track_distribution = {}

        for submission in submissions:
            # Get project to find track
            project_id = submission.get("project_id")
            projects = await zerodb_client.tables.query_rows(
                "projects", filter={"project_id": project_id}, limit=1
            )

            if projects:
                track_id = projects[0].get("track_id", "unspecified")
                track_distribution[track_id] = track_distribution.get(track_id, 0) + 1

        # Build stats
        stats = {
            "participant_count": participant_count,
            "team_count": team_count,
            "submission_count": submission_count,
            "builder_count": builder_count,
            "judge_count": judge_count,
            "track_distribution": track_distribution,
        }

        # Build recent activity (last 10 activities)
        recent_activity = []

        # Add team creation activities
        for team in teams[-10:]:
            recent_activity.append(
                {
                    "activity_type": "team_created",
                    "description": f"Team '{team.get('name')}' created",
                    "timestamp": team.get("created_at"),
                    "metadata": {"team_id": team.get("team_id")},
                }
            )

        # Add submission activities
        for submission in submissions[-10:]:
            # Get project name
            project_id = submission.get("project_id")
            projects = await zerodb_client.tables.query_rows(
                "projects", filter={"project_id": project_id}, limit=1
            )
            project_name = projects[0].get("name") if projects else "Unknown Project"

            recent_activity.append(
                {
                    "activity_type": "submission_made",
                    "description": f"Project '{project_name}' submitted",
                    "timestamp": submission.get("submitted_at"),
                    "metadata": {"submission_id": submission.get("submission_id")},
                }
            )

        # Add participant join activities
        for participant in participants[-10:]:
            metadata = participant.get("metadata", {})
            user_name = metadata.get("ainative_user_name", "A user")

            recent_activity.append(
                {
                    "activity_type": "participant_joined",
                    "description": f"{user_name} joined as {participant.get('role')}",
                    "timestamp": participant.get("joined_at"),
                    "metadata": {"participant_id": participant.get("participant_id")},
                }
            )

        # Sort by timestamp descending and take last 10
        recent_activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        recent_activity = recent_activity[:10]

        logger.info(
            f"Hackathon overview: {participant_count} participants, "
            f"{team_count} teams, {submission_count} submissions"
        )

        return {
            "hackathon_id": hackathon_id,
            "name": hackathon.get("name"),
            "description": hackathon.get("description"),
            "status": hackathon.get("status"),
            "start_date": hackathon.get("start_date"),
            "end_date": hackathon.get("end_date"),
            "location": hackathon.get("location"),
            "stats": stats,
            "recent_activity": recent_activity,
        }

    except HTTPException:
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout fetching hackathon overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error fetching hackathon overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch hackathon overview. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error in get_hackathon_overview: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch hackathon overview. Please contact support.",
        )
