"""
API routes for project management.

Provides endpoints for creating, reading, updating, and deleting hackathon projects.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_user, get_zerodb_client
from api.schemas.project import (
    ErrorResponse,
    ProjectCreateRequest,
    ProjectDeleteResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatusUpdateRequest,
    ProjectUpdateRequest,
)
from integrations.zerodb.client import ZeroDBClient
from services import project_service
from services.authorization import check_team_member


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1", tags=["projects"])


@router.post(
    "/hackathons/{hackathon_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a team member"},
        404: {"model": ErrorResponse, "description": "Hackathon or team not found"},
        409: {"model": ErrorResponse, "description": "Team already has a project"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_project(
    hackathon_id: str,
    request: ProjectCreateRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Create a new project for a team.

    Only team members can create a project for their team.
    One project per team per hackathon is allowed.

    **Authorization:** Requires team membership

    **Status Transitions:**
    - New projects start in IDEA status
    - IDEA → BUILDING → SUBMITTED
    """
    logger.info(
        f"User {current_user.get('user_id')} creating project for team {request.team_id}"
    )

    # Verify user is a team member
    await check_team_member(current_user.get("user_id"), request.team_id, zerodb)

    # Create project
    project = await project_service.create_project(
        hackathon_id=hackathon_id,
        team_id=request.team_id,
        title=request.title,
        one_liner=request.one_liner,
        repo_url=request.repo_url,
        demo_url=request.demo_url,
        zerodb=zerodb,
    )

    return ProjectResponse(**project)


@router.get(
    "/hackathons/{hackathon_id}/projects",
    response_model=ProjectListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_projects(
    hackathon_id: str,
    status_filter: Optional[str] = Query(
        None, description="Filter by status (IDEA, BUILDING, SUBMITTED)"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    List all projects in a hackathon.

    Supports filtering by status and pagination.

    **Authorization:** Requires authentication
    """
    logger.info(f"User {current_user.get('user_id')} listing projects for hackathon {hackathon_id}")

    result = await project_service.list_projects(
        hackathon_id=hackathon_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
        zerodb=zerodb,
    )

    return ProjectListResponse(
        projects=[ProjectResponse(**p) for p in result["projects"]],
        total=result["total"],
        skip=result["skip"],
        limit=result["limit"],
    )


@router.get(
    "/hackathons/{hackathon_id}/projects/{project_id}",
    response_model=ProjectResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_project(
    hackathon_id: str,
    project_id: str,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Get a single project by ID.

    **Authorization:** Requires authentication
    """
    logger.info(f"User {current_user.get('user_id')} retrieving project {project_id}")

    project = await project_service.get_project(project_id, zerodb)

    # Verify project belongs to hackathon
    if project.get("hackathon_id") != hackathon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found in hackathon {hackathon_id}",
        )

    return ProjectResponse(**project)


@router.get(
    "/teams/{team_id}/project",
    response_model=Optional[ProjectResponse],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Team not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_team_project(
    team_id: str,
    hackathon_id: str = Query(..., description="Hackathon ID"),
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Get a team's project in a specific hackathon.

    Returns null if team has no project.

    **Authorization:** Requires authentication
    """
    logger.info(
        f"User {current_user.get('user_id')} retrieving project for team {team_id}"
    )

    project = await project_service.get_team_project(team_id, hackathon_id, zerodb)

    if project:
        return ProjectResponse(**project)
    return None


@router.put(
    "/hackathons/{hackathon_id}/projects/{project_id}",
    response_model=ProjectResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a team member"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_project(
    hackathon_id: str,
    project_id: str,
    request: ProjectUpdateRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Update a project's details.

    Only team members can update their team's project.

    **Authorization:** Requires team membership
    """
    logger.info(f"User {current_user.get('user_id')} updating project {project_id}")

    # Get project
    project = await project_service.get_project(project_id, zerodb)

    # Verify project belongs to hackathon
    if project.get("hackathon_id") != hackathon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found in hackathon {hackathon_id}",
        )

    # Verify user is a team member
    await check_team_member(current_user.get("user_id"), project["team_id"], zerodb)

    # Build update dict (only include non-None fields)
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}

    if not update_data:
        # No fields to update, return current project
        return ProjectResponse(**project)

    # Update project
    updated_project = await project_service.update_project(
        project_id, update_data, zerodb
    )

    return ProjectResponse(**updated_project)


@router.patch(
    "/hackathons/{hackathon_id}/projects/{project_id}/status",
    response_model=ProjectResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid status transition"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a team member"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_project_status(
    hackathon_id: str,
    project_id: str,
    request: ProjectStatusUpdateRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Update a project's status.

    Validates status transitions:
    - IDEA → BUILDING
    - BUILDING → SUBMITTED
    - SUBMITTED (terminal state, no further transitions)

    Only team members can update their team's project status.

    **Authorization:** Requires team membership
    """
    logger.info(
        f"User {current_user.get('user_id')} updating project {project_id} status to {request.status}"
    )

    # Get project
    project = await project_service.get_project(project_id, zerodb)

    # Verify project belongs to hackathon
    if project.get("hackathon_id") != hackathon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found in hackathon {hackathon_id}",
        )

    # Verify user is a team member
    await check_team_member(current_user.get("user_id"), project["team_id"], zerodb)

    # Update status (validates transition)
    updated_project = await project_service.update_project_status(
        project_id, request.status, zerodb
    )

    return ProjectResponse(**updated_project)


@router.delete(
    "/hackathons/{hackathon_id}/projects/{project_id}",
    response_model=ProjectDeleteResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not a team member"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_project(
    hackathon_id: str,
    project_id: str,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Delete a project.

    Only team members can delete their team's project.

    **Authorization:** Requires team membership
    """
    logger.info(f"User {current_user.get('user_id')} deleting project {project_id}")

    # Get project
    project = await project_service.get_project(project_id, zerodb)

    # Verify project belongs to hackathon
    if project.get("hackathon_id") != hackathon_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found in hackathon {hackathon_id}",
        )

    # Verify user is a team member
    await check_team_member(current_user.get("user_id"), project["team_id"], zerodb)

    # Delete project
    await project_service.delete_project(project_id, zerodb)

    return ProjectDeleteResponse(
        success=True, message=f"Project {project_id} deleted successfully"
    )
