"""
Project Management API Routes

Provides REST endpoints for hackathon project CRUD operations and status management.
All endpoints require authentication via AINative Studio.
"""

import logging
from typing import Any, Dict, Optional

from api.dependencies import get_current_user
from api.schemas.project import (
    ErrorResponse,
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatusUpdateRequest,
    ProjectUpdateRequest,
    SuccessResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import ZeroDBError
from services.project_service import (
    create_project,
    delete_project,
    get_project,
    get_team_project,
    list_projects,
    update_project,
    update_project_status,
)

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router with /v1 prefix
router = APIRouter(prefix="/v1/hackathons", tags=["Projects"])


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
    "/{hackathon_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Project created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request or duplicate project"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Team not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Create Project",
    description="""
    Create a new project for a team in a hackathon.

    - Enforces one project per team per hackathon
    - Project starts in IDEA status
    - Requires authentication and team membership

    **Authorization:** User must be a team member
    """,
)
async def create_project_endpoint(
    hackathon_id: str = Path(..., description="Hackathon UUID"),
    request: ProjectCreateRequest = ...,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Create a new project.

    Args:
        hackathon_id: Hackathon UUID
        request: Project creation request with team_id, title, etc.
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Created project details

    Raises:
        HTTPException: 400 for validation/duplicate, 404 for team not found, 500 for server errors
    """
    try:
        logger.info(
            f"Creating project '{request.title}' for team {request.team_id}",
            extra={
                "user_id": current_user.get("id"),
                "hackathon_id": hackathon_id,
                "team_id": request.team_id,
            },
        )

        project = await create_project(
            zerodb_client=zerodb_client,
            hackathon_id=hackathon_id,
            team_id=str(request.team_id),
            title=request.title,
            creator_id=str(current_user.get("id")),
            one_liner=request.one_liner,
            description=request.description,
            repo_url=request.repo_url,
            demo_url=request.demo_url,
            video_url=request.video_url,
        )

        logger.info(
            f"Project created successfully: {project.get('project_id')}",
            extra={"project_id": project.get("project_id")},
        )

        return project

    except ValueError as e:
        logger.warning(f"Validation error creating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error creating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project. Please try again later.",
        )


@router.get(
    "/{hackathon_id}/projects",
    response_model=ProjectListResponse,
    responses={
        200: {"description": "Projects retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="List Projects",
    description="""
    List projects for a hackathon with optional filtering.

    - Supports pagination via skip/limit
    - Optional status filter (IDEA, BUILDING, SUBMITTED)
    - Optional team ID filter
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def list_projects_endpoint(
    hackathon_id: str = Path(..., description="Hackathon UUID"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by project status (IDEA, BUILDING, SUBMITTED)"
    ),
    team_id: Optional[str] = Query(
        None, description="Filter by team ID"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    List projects for a hackathon.

    Args:
        hackathon_id: Hackathon UUID to filter projects
        status_filter: Optional status filter
        team_id: Optional team ID filter
        skip: Pagination offset
        limit: Maximum results to return
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        List of projects with pagination metadata

    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(
            f"Listing projects for hackathon {hackathon_id}",
            extra={
                "user_id": current_user.get("id"),
                "hackathon_id": hackathon_id,
                "skip": skip,
                "limit": limit,
            },
        )

        projects = await list_projects(
            zerodb_client=zerodb_client,
            hackathon_id=hackathon_id,
            requester_id=str(current_user.get("id")),
            status=status_filter,
            team_id=team_id,
            skip=skip,
            limit=limit,
        )

        return {
            "projects": projects,
            "total": len(projects),
            "skip": skip,
            "limit": limit,
        }

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error listing projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list projects. Please try again later.",
        )


@router.get(
    "/{hackathon_id}/projects/{project_id}",
    response_model=ProjectDetailResponse,
    responses={
        200: {"description": "Project retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Get Project Details",
    description="""
    Get detailed information about a project.

    - Returns all project metadata
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def get_project_endpoint(
    hackathon_id: str = Path(..., description="Hackathon UUID"),
    project_id: str = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Get project details.

    Args:
        hackathon_id: Hackathon UUID (for routing consistency)
        project_id: Project UUID
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Project details

    Raises:
        HTTPException: 404 if project not found, 500 for server errors
    """
    try:
        logger.info(
            f"Getting project details: {project_id}",
            extra={"user_id": current_user.get("id"), "project_id": project_id},
        )

        project = await get_project(
            zerodb_client=zerodb_client,
            project_id=project_id,
            requester_id=str(current_user.get("id")),
        )

        return project

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error getting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project. Please try again later.",
        )


@router.put(
    "/{hackathon_id}/projects/{project_id}",
    response_model=ProjectResponse,
    responses={
        200: {"description": "Project updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - not a team member"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Update Project",
    description="""
    Update project details.

    - All fields are optional
    - Only provided fields will be updated
    - Requires authentication and team membership

    **Authorization:** User must be a team member
    """,
)
async def update_project_endpoint(
    hackathon_id: str = Path(..., description="Hackathon UUID"),
    project_id: str = Path(..., description="Project UUID"),
    request: ProjectUpdateRequest = ...,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Update project details.

    Args:
        hackathon_id: Hackathon UUID (for routing consistency)
        project_id: Project UUID to update
        request: Project update request with optional fields
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Updated project details

    Raises:
        HTTPException: 400 for validation, 403 for unauthorized, 404 if not found, 500 for server errors
    """
    try:
        logger.info(
            f"Updating project: {project_id}",
            extra={"user_id": current_user.get("id"), "project_id": project_id},
        )

        updated_project = await update_project(
            zerodb_client=zerodb_client,
            project_id=project_id,
            requester_id=str(current_user.get("id")),
            title=request.title,
            one_liner=request.one_liner,
            description=request.description,
            repo_url=request.repo_url,
            demo_url=request.demo_url,
            video_url=request.video_url,
        )

        logger.info(
            f"Project updated successfully: {project_id}",
            extra={"project_id": project_id},
        )

        return updated_project

    except ValueError as e:
        logger.warning(f"Validation error updating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error updating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project. Please try again later.",
        )


@router.patch(
    "/{hackathon_id}/projects/{project_id}/status",
    response_model=ProjectResponse,
    responses={
        200: {"description": "Project status updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid status value"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - not a team member"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Update Project Status",
    description="""
    Update project status.

    - Valid statuses: IDEA, BUILDING, SUBMITTED
    - Requires authentication and team membership

    **Authorization:** User must be a team member
    """,
)
async def update_project_status_endpoint(
    hackathon_id: str = Path(..., description="Hackathon UUID"),
    project_id: str = Path(..., description="Project UUID"),
    request: ProjectStatusUpdateRequest = ...,
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Update project status.

    Args:
        hackathon_id: Hackathon UUID (for routing consistency)
        project_id: Project UUID to update
        request: Status update request
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Updated project details

    Raises:
        HTTPException: 400 for invalid status, 403 for unauthorized, 404 if not found, 500 for server errors
    """
    try:
        logger.info(
            f"Updating project {project_id} status to {request.status}",
            extra={
                "user_id": current_user.get("id"),
                "project_id": project_id,
                "new_status": request.status,
            },
        )

        updated_project = await update_project_status(
            zerodb_client=zerodb_client,
            project_id=project_id,
            status=request.status,
            requester_id=str(current_user.get("id")),
        )

        logger.info(
            f"Project status updated successfully: {project_id}",
            extra={"project_id": project_id, "status": request.status},
        )

        return updated_project

    except ValueError as e:
        logger.warning(f"Validation error updating status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error updating project status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project status. Please try again later.",
        )


@router.delete(
    "/{hackathon_id}/projects/{project_id}",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Project deleted successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - not a team member"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Delete Project",
    description="""
    Delete a project.

    - Removes project permanently
    - Cannot be undone
    - Requires authentication and team membership

    **Authorization:** User must be a team member
    """,
)
async def delete_project_endpoint(
    hackathon_id: str = Path(..., description="Hackathon UUID"),
    project_id: str = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Delete a project.

    Args:
        hackathon_id: Hackathon UUID (for routing consistency)
        project_id: Project UUID to delete
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Success confirmation

    Raises:
        HTTPException: 403 for unauthorized, 404 if not found, 500 for server errors
    """
    try:
        logger.info(
            f"Deleting project: {project_id}",
            extra={"user_id": current_user.get("id"), "project_id": project_id},
        )

        result = await delete_project(
            zerodb_client=zerodb_client,
            project_id=project_id,
            requester_id=str(current_user.get("id")),
        )

        logger.info(
            f"Project deleted successfully: {project_id}",
            extra={"project_id": project_id},
        )

        return {"success": True, "message": "Project deleted successfully"}

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except ZeroDBError as e:
        logger.error(f"Database error deleting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project. Please contact support.",
        )
    except Exception as e:
        logger.exception(f"Unexpected error deleting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project. Please try again later.",
        )


@router.get(
    "/teams/{team_id}/project",
    response_model=ProjectDetailResponse,
    responses={
        200: {"description": "Project retrieved successfully"},
        204: {"description": "No project found for team"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        504: {"model": ErrorResponse, "description": "Request timeout"},
    },
    summary="Get Team's Project",
    description="""
    Get a team's project (if any).

    - Returns project if team has one
    - Returns 204 if team has no project
    - Requires authentication

    **Authorization:** User must be authenticated
    """,
)
async def get_team_project_endpoint(
    team_id: str = Path(..., description="Team UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    zerodb_client: ZeroDBClient = Depends(get_zerodb_client),
) -> Dict[str, Any]:
    """
    Get a team's project.

    Args:
        team_id: Team UUID
        current_user: Authenticated user from dependency
        zerodb_client: ZeroDB client from dependency

    Returns:
        Project details or None

    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(
            f"Getting project for team: {team_id}",
            extra={"user_id": current_user.get("id"), "team_id": team_id},
        )

        project = await get_team_project(
            zerodb_client=zerodb_client,
            team_id=team_id,
            requester_id=str(current_user.get("id")),
        )

        if not project:
            raise HTTPException(
                status_code=status.HTTP_204_NO_CONTENT,
                detail="Team has no project",
            )

        return project

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.exception(f"Unexpected error getting team project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team project. Please try again later.",
        )
