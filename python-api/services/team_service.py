"""
Team Management Service

Provides team CRUD operations and member management for hackathons.
Uses ZeroDB tables API for data persistence.
"""

import logging
import uuid
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

# Type for valid team status
TeamStatus = Literal["FORMING", "ACTIVE", "SUBMITTED"]

# Type for valid team member roles
MemberRole = Literal["LEAD", "MEMBER"]


async def create_team(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    name: str,
    creator_id: str,
    track_id: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new team for a hackathon.

    Automatically adds the creator as team LEAD. Team starts in FORMING status.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: Hackathon ID the team belongs to
        name: Team name (required, non-empty)
        creator_id: User ID of team creator (becomes LEAD)
        track_id: Optional track ID
        description: Optional team description

    Returns:
        Dict with team details including team_id

    Raises:
        ValueError: If name is empty or invalid
        HTTPException: 500 if database error occurs

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> team = await create_team(
        ...     client,
        ...     hackathon_id="hack-123",
        ...     name="Team Alpha",
        ...     creator_id="user-456"
        ... )
        >>> print(team["team_id"])
    """
    try:
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Team name cannot be empty")

        # Generate team ID
        team_id = str(uuid.uuid4())

        # Prepare team data
        team_data = {
            "team_id": team_id,
            "hackathon_id": hackathon_id,
            "name": name.strip(),
            "status": "FORMING",
        }

        if track_id:
            team_data["track_id"] = track_id
        if description:
            team_data["description"] = description

        # Insert team
        await zerodb_client.tables.insert_rows(
            "teams",
            rows=[team_data]
        )

        logger.info(f"Created team {team_id} for hackathon {hackathon_id}")

        # Add creator as team LEAD
        member_id = str(uuid.uuid4())
        member_data = {
            "id": member_id,
            "team_id": team_id,
            "participant_id": creator_id,
            "role": "LEAD",
        }

        await zerodb_client.tables.insert_rows(
            "team_members",
            rows=[member_data]
        )

        logger.info(
            f"Added creator {creator_id} as LEAD to team {team_id}"
        )

        # Fetch and return created team
        teams = await zerodb_client.tables.query_rows(
            "teams",
            filter={"team_id": team_id},
            limit=1
        )

        return teams[0]

    except ValueError:
        # Re-raise validation errors
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout creating team: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error creating team: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create team. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error creating team: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create team. Please contact support.",
        )


async def add_team_member(
    zerodb_client: ZeroDBClient,
    team_id: str,
    participant_id: str,
    role: MemberRole,
    requester_id: str,
) -> Dict[str, Any]:
    """
    Add a member to a team.

    Args:
        zerodb_client: ZeroDB client instance
        team_id: Team ID to add member to
        participant_id: Participant ID to add
        role: Member role (LEAD or MEMBER)
        requester_id: User ID making the request (for future authorization)

    Returns:
        Dict with member details

    Raises:
        ValueError: If role is invalid
        HTTPException: 404 if team not found
        HTTPException: 400 if member already in team
        HTTPException: 500 if database error

    Example:
        >>> await add_team_member(
        ...     client,
        ...     team_id="team-123",
        ...     participant_id="user-789",
        ...     role="MEMBER",
        ...     requester_id="user-456"
        ... )
    """
    try:
        # Validate role
        if role not in ["LEAD", "MEMBER"]:
            raise ValueError(f"Invalid role: {role}. Must be 'LEAD' or 'MEMBER'")

        # Check if team exists
        teams = await zerodb_client.tables.query_rows(
            "teams",
            filter={"team_id": team_id},
            limit=1
        )

        if not teams:
            logger.warning(f"Team not found: {team_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Team {team_id} not found",
            )

        # Check if participant is already a member
        existing_members = await zerodb_client.tables.query_rows(
            "team_members",
            filter={"team_id": team_id, "participant_id": participant_id},
            limit=1
        )

        if existing_members:
            logger.warning(
                f"Participant {participant_id} already in team {team_id}"
            )
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Participant is already a member of this team",
            )

        # Add member
        member_id = str(uuid.uuid4())
        member_data = {
            "id": member_id,
            "team_id": team_id,
            "participant_id": participant_id,
            "role": role,
        }

        await zerodb_client.tables.insert_rows(
            "team_members",
            rows=[member_data]
        )

        logger.info(
            f"Added participant {participant_id} as {role} to team {team_id}"
        )

        return {
            "id": member_id,
            "team_id": team_id,
            "participant_id": participant_id,
            "role": role,
        }

    except ValueError:
        # Re-raise validation errors
        raise

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout adding team member: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error adding team member: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add team member. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error adding team member: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add team member. Please contact support.",
        )


async def remove_team_member(
    zerodb_client: ZeroDBClient,
    team_id: str,
    participant_id: str,
    requester_id: str,
) -> Dict[str, Any]:
    """
    Remove a member from a team.

    Prevents removing the last LEAD from the team.

    Args:
        zerodb_client: ZeroDB client instance
        team_id: Team ID
        participant_id: Participant ID to remove
        requester_id: User ID making the request (for future authorization)

    Returns:
        Dict with success status

    Raises:
        HTTPException: 404 if member not found
        HTTPException: 400 if attempting to remove last LEAD
        HTTPException: 500 if database error

    Example:
        >>> await remove_team_member(
        ...     client,
        ...     team_id="team-123",
        ...     participant_id="user-789",
        ...     requester_id="user-456"
        ... )
    """
    try:
        # Find member
        members = await zerodb_client.tables.query_rows(
            "team_members",
            filter={"team_id": team_id, "participant_id": participant_id},
            limit=1
        )

        if not members:
            logger.warning(
                f"Member {participant_id} not found in team {team_id}"
            )
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Member not found in team",
            )

        member = members[0]

        # If removing a LEAD, check if there are other LEADs
        if member.get("role") == "LEAD":
            all_leads = await zerodb_client.tables.query_rows(
                "team_members",
                filter={"team_id": team_id, "role": "LEAD"}
            )

            # Filter out current member from leads
            other_leads = [
                lead for lead in all_leads
                if lead.get("participant_id") != participant_id
            ]

            if not other_leads:
                logger.warning(
                    f"Cannot remove last LEAD from team {team_id}"
                )
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last LEAD from the team",
                )

        # Remove member
        member_id = member.get("id")
        await zerodb_client.tables.delete_row("team_members", member_id)

        logger.info(
            f"Removed participant {participant_id} from team {team_id}"
        )

        return {"success": True}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout removing team member: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error removing team member: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove team member. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error removing team member: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove team member. Please contact support.",
        )


async def get_team(
    zerodb_client: ZeroDBClient,
    team_id: str,
    requester_id: str,
) -> Dict[str, Any]:
    """
    Get team details including members.

    Args:
        zerodb_client: ZeroDB client instance
        team_id: Team ID to retrieve
        requester_id: User ID making the request (for future authorization)

    Returns:
        Dict with team details and members list

    Raises:
        HTTPException: 404 if team not found
        HTTPException: 500 if database error

    Example:
        >>> team = await get_team(
        ...     client,
        ...     team_id="team-123",
        ...     requester_id="user-456"
        ... )
        >>> print(team["name"], team["member_count"])
    """
    try:
        # Get team
        teams = await zerodb_client.tables.query_rows(
            "teams",
            filter={"team_id": team_id},
            limit=1
        )

        if not teams:
            logger.warning(f"Team not found: {team_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Team {team_id} not found",
            )

        team = teams[0]

        # Get team members
        members = await zerodb_client.tables.query_rows(
            "team_members",
            filter={"team_id": team_id}
        )

        # Add members to team data
        team["members"] = members
        team["member_count"] = len(members)

        return team

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout getting team: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error getting team: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error getting team: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team. Please contact support.",
        )


async def list_teams(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    requester_id: str,
    status: Optional[TeamStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    List teams for a hackathon.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: Hackathon ID to list teams for
        requester_id: User ID making the request (for future authorization)
        status: Optional status filter (FORMING, ACTIVE, SUBMITTED)
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return (pagination)

    Returns:
        List of team dictionaries

    Raises:
        HTTPException: 500 if database error

    Example:
        >>> teams = await list_teams(
        ...     client,
        ...     hackathon_id="hack-123",
        ...     status="ACTIVE",
        ...     requester_id="user-456"
        ... )
        >>> print(f"Found {len(teams)} active teams")
    """
    try:
        # Build filter
        filter_dict = {"hackathon_id": hackathon_id}
        if status:
            filter_dict["status"] = status

        # Query teams
        teams = await zerodb_client.tables.query_rows(
            "teams",
            filter=filter_dict,
            skip=skip,
            limit=limit
        )

        logger.info(
            f"Listed {len(teams)} teams for hackathon {hackathon_id}"
        )

        return teams

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout listing teams: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error listing teams: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list teams. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error listing teams: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list teams. Please contact support.",
        )


async def update_team(
    zerodb_client: ZeroDBClient,
    team_id: str,
    requester_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[TeamStatus] = None,
    track_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update team details.

    Args:
        zerodb_client: ZeroDB client instance
        team_id: Team ID to update
        requester_id: User ID making the request (for future authorization)
        name: Optional new team name
        description: Optional new description
        status: Optional new status (FORMING, ACTIVE, SUBMITTED)
        track_id: Optional new track ID

    Returns:
        Dict with updated team details

    Raises:
        ValueError: If status is invalid
        HTTPException: 404 if team not found
        HTTPException: 500 if database error

    Example:
        >>> team = await update_team(
        ...     client,
        ...     team_id="team-123",
        ...     name="Updated Team Name",
        ...     status="ACTIVE",
        ...     requester_id="user-456"
        ... )
    """
    try:
        # Validate status if provided
        if status and status not in ["FORMING", "ACTIVE", "SUBMITTED"]:
            raise ValueError(
                f"Invalid status: {status}. "
                "Must be 'FORMING', 'ACTIVE', or 'SUBMITTED'"
            )

        # Check if team exists
        teams = await zerodb_client.tables.query_rows(
            "teams",
            filter={"team_id": team_id},
            limit=1
        )

        if not teams:
            logger.warning(f"Team not found: {team_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Team {team_id} not found",
            )

        # Build update data
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if status is not None:
            update_data["status"] = status
        if track_id is not None:
            update_data["track_id"] = track_id

        # Update team
        updated_team = await zerodb_client.tables.update_row(
            "teams",
            team_id,
            data=update_data
        )

        logger.info(f"Updated team {team_id}")

        return updated_team

    except ValueError:
        # Re-raise validation errors
        raise

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout updating team: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error updating team: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error updating team: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team. Please contact support.",
        )
