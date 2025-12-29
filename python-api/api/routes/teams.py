"""
Team Management API Routes

Provides REST endpoints for team CRUD operations and member management.
All endpoints require authentication via AINative Studio.
"""

import logging
from typing import Any, Dict, List, Optional

from api.dependencies import get_current_user
from api.schemas.teams import (
    ErrorResponse,
    TeamCreateRequest,
    TeamDeleteResponse,
    TeamDetailResponse,
    TeamListResponse,
    TeamMemberAddRequest,
    TeamMemberAddResponse,
    TeamMemberRemoveResponse,
    TeamResponse,
    TeamUpdateRequest,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBError
from services.team_service import (
    add_team_member,
    create_team,
    get_team,
    list_teams,
    remove_team_member,
    update_team,
)

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/teams", tags=["Teams"])


# Dependency: Get ZeroDB client
async def get_zerodb_client() -> ZeroDBClient:
    """
    Dependency to provide ZeroDB client instance.

    Returns:
        ZeroDBClient instance configured with environment credentials

    Raises:
        HTTPException: 503 if ZeroDB client cannot be initialized
    """
    try:
        client = ZeroDBClient()
        return client
    except ValueError as e:
        logger.error(f"Failed to initialize ZeroDB client: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please contact support.",
        )


@router.post(
    "",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Team created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Create Team",
    description="""
    Create a new team for a hackathon.

    - Automatically adds the creator as team LEAD
    - Team starts in FORMING status
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def create_team_endpoint(
    request: TeamCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Create a new team.

    Args:
        request: Team creation request with hackathon_id, name, etc.
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Created team details

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        logger.info(
            f"Creating team '{request.name}' for hackathon {request.hackathon_id}",
            extra={
                "user_id": current_user.get("id"),
                "hackathon_id": request.hackathon_id,
            },
        )

        team = await create_team(
            zerodb_client=zerodb_client,
            hackathon_id=request.hackathon_id,
            name=request.name,
            creator_id=str(current_user.get("id")),
            track_id=request.track_id,
            description=request.description,
        )

        logger.info(
            f"Team created successfully: {team.get('team_id')}",
            extra={"team_id": team.get("team_id")},
        )

        return team

    except ValueError as e:
        logger.warning(f"Validation error creating team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error creating team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create team. Please try again later.",
        )


@router.get(
    "",
    response_model=TeamListResponse,
    responses={
        200: {"description": "Teams retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="List Teams",
    description="""
    List teams for a hackathon with optional filtering.

    - Supports pagination via skip/limit
    - Optional status filter
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def list_teams_endpoint(
    hackathon_id: str = Query(..., description="Hackathon UUID to list teams for"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by team status (FORMING, ACTIVE, SUBMITTED)"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    List teams for a hackathon.

    Args:
        hackathon_id: Hackathon UUID to filter teams
        status_filter: Optional status filter
        skip: Pagination offset
        limit: Maximum results to return
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        List of teams with pagination metadata

    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(
            f"Listing teams for hackathon {hackathon_id}",
            extra={
                "user_id": current_user.get("id"),
                "hackathon_id": hackathon_id,
                "skip": skip,
                "limit": limit,
            },
        )

        teams = await list_teams(
            zerodb_client=zerodb_client,
            hackathon_id=hackathon_id,
            requester_id=str(current_user.get("id")),
            status=status_filter,
            skip=skip,
            limit=limit,
        )

        return {
            "teams": teams,
            "total": len(teams),
            "skip": skip,
            "limit": limit,
        }

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error listing teams: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list teams. Please try again later.",
        )


@router.get(
    "/{team_id}",
    response_model=TeamDetailResponse,
    responses={
        200: {"description": "Team retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Team not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Get Team Details",
    description="""
    Get detailed information about a team including members.

    - Returns team metadata
    - Includes full member list
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def get_team_endpoint(
    team_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Get team details with members.

    Args:
        team_id: Team UUID
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Team details with member list

    Raises:
        HTTPException: 404 if team not found, 500 for server errors
    """
    try:
        logger.info(
            f"Getting team details: {team_id}",
            extra={"user_id": current_user.get("id"), "team_id": team_id},
        )

        team = await get_team(
            zerodb_client=zerodb_client,
            team_id=team_id,
            requester_id=str(current_user.get("id")),
        )

        return team

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error getting team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team. Please try again later.",
        )


@router.put(
    "/{team_id}",
    response_model=TeamResponse,
    responses={
        200: {"description": "Team updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Team not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Update Team",
    description="""
    Update team details.

    - All fields are optional
    - Only provided fields will be updated
    - Requires authentication

    **Authorization:** User must be authenticated (team lead recommended)
    """,
)
async def update_team_endpoint(
    team_id: str,
    request: TeamUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Update team details.

    Args:
        team_id: Team UUID to update
        request: Team update request with optional fields
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Updated team details

    Raises:
        HTTPException: 400 for validation, 404 if not found, 500 for server errors
    """
    try:
        logger.info(
            f"Updating team: {team_id}",
            extra={"user_id": current_user.get("id"), "team_id": team_id},
        )

        updated_team = await update_team(
            zerodb_client=zerodb_client,
            team_id=team_id,
            requester_id=str(current_user.get("id")),
            name=request.name,
            description=request.description,
            status=request.status,
            track_id=request.track_id,
        )

        logger.info(
            f"Team updated successfully: {team_id}",
            extra={"team_id": team_id},
        )

        return updated_team

    except ValueError as e:
        logger.warning(f"Validation error updating team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error updating team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team. Please try again later.",
        )


@router.delete(
    "/{team_id}",
    response_model=TeamDeleteResponse,
    responses={
        200: {"description": "Team deleted successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Team not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Delete Team",
    description="""
    Delete a team.

    - Removes team and all associated members
    - Cannot be undone
    - Requires authentication

    **Authorization:** User must be authenticated (team lead or admin recommended)
    """,
)
async def delete_team_endpoint(
    team_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Delete a team.

    Args:
        team_id: Team UUID to delete
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Success confirmation

    Raises:
        HTTPException: 404 if not found, 500 for server errors
    """
    try:
        logger.info(
            f"Deleting team: {team_id}",
            extra={"user_id": current_user.get("id"), "team_id": team_id},
        )

        # Check if team exists
        team = await get_team(
            zerodb_client=zerodb_client,
            team_id=team_id,
            requester_id=str(current_user.get("id")),
        )

        # Delete team members first
        if team.get("members"):
            for member in team["members"]:
                await zerodb_client.tables.delete_row("team_members", member["id"])

        # Delete team
        await zerodb_client.tables.delete_row("teams", team_id)

        logger.info(
            f"Team deleted successfully: {team_id}",
            extra={"team_id": team_id},
        )

        return {"success": True, "message": "Team deleted successfully"}

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except ZeroDBError as e:
        logger.error(f"Database error deleting team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete team. Please contact support.",
        )
    except Exception as e:
        logger.exception(f"Unexpected error deleting team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete team. Please try again later.",
        )


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberAddResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Member added successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request or member already exists"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Team not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Add Team Member",
    description="""
    Add a member to a team.

    - Prevents duplicate members
    - Supports LEAD or MEMBER role
    - Requires authentication

    **Authorization:** User must be authenticated (team lead recommended)
    """,
)
async def add_team_member_endpoint(
    team_id: str,
    request: TeamMemberAddRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Add a member to a team.

    Args:
        team_id: Team UUID
        request: Member add request with participant_id and role
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Added member details

    Raises:
        HTTPException: 400 if duplicate, 404 if team not found, 500 for server errors
    """
    try:
        logger.info(
            f"Adding member to team {team_id}",
            extra={
                "user_id": current_user.get("id"),
                "team_id": team_id,
                "participant_id": request.participant_id,
                "role": request.role,
            },
        )

        member = await add_team_member(
            zerodb_client=zerodb_client,
            team_id=team_id,
            participant_id=request.participant_id,
            role=request.role,
            requester_id=str(current_user.get("id")),
        )

        logger.info(
            f"Member added successfully to team {team_id}",
            extra={
                "team_id": team_id,
                "participant_id": request.participant_id,
            },
        )

        return member

    except ValueError as e:
        logger.warning(f"Validation error adding member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error adding team member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add team member. Please try again later.",
        )


@router.delete(
    "/{team_id}/members/{participant_id}",
    response_model=TeamMemberRemoveResponse,
    responses={
        200: {"description": "Member removed successfully"},
        400: {"model": ErrorResponse, "description": "Cannot remove last LEAD"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Member not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Remove Team Member",
    description="""
    Remove a member from a team.

    - Prevents removing the last LEAD
    - Requires authentication

    **Authorization:** User must be authenticated (team lead recommended)
    """,
)
async def remove_team_member_endpoint(
    team_id: str,
    participant_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Remove a member from a team.

    Args:
        team_id: Team UUID
        participant_id: Participant UUID to remove
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Success confirmation

    Raises:
        HTTPException: 400 if last LEAD, 404 if not found, 500 for server errors
    """
    try:
        logger.info(
            f"Removing member from team {team_id}",
            extra={
                "user_id": current_user.get("id"),
                "team_id": team_id,
                "participant_id": participant_id,
            },
        )

        result = await remove_team_member(
            zerodb_client=zerodb_client,
            team_id=team_id,
            participant_id=participant_id,
            requester_id=str(current_user.get("id")),
        )

        logger.info(
            f"Member removed successfully from team {team_id}",
            extra={"team_id": team_id, "participant_id": participant_id},
        )

        return {"success": result["success"], "message": "Member removed successfully"}

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error removing team member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove team member. Please try again later.",
        )
