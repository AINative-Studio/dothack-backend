"""
Project Management Service

Provides project CRUD operations and status management for hackathons.
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

# Type for valid project status
ProjectStatus = Literal["IDEA", "BUILDING", "SUBMITTED"]


async def create_project(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    team_id: str,
    title: str,
    creator_id: str,
    one_liner: Optional[str] = None,
    description: Optional[str] = None,
    repo_url: Optional[str] = None,
    demo_url: Optional[str] = None,
    video_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new project for a team in a hackathon.

    Enforces one project per team per hackathon constraint.
    Project starts in IDEA status.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: Hackathon ID the project belongs to
        team_id: Team ID creating the project
        title: Project title (required, non-empty)
        creator_id: User ID of project creator (for authorization)
        one_liner: Short project description
        description: Detailed project description
        repo_url: Repository URL
        demo_url: Demo/deployment URL
        video_url: Demo video URL

    Returns:
        Dict with project details including project_id

    Raises:
        ValueError: If title is empty or URLs are invalid
        HTTPException: 400 if team already has a project, 500 if database error

    Example:
        >>> client = ZeroDBClient(api_key="...", project_id="...")
        >>> project = await create_project(
        ...     client,
        ...     hackathon_id="hack-123",
        ...     team_id="team-456",
        ...     title="AI-Powered Code Review",
        ...     creator_id="user-789"
        ... )
        >>> print(project["project_id"])
    """
    try:
        # Validate inputs
        if not title or not title.strip():
            raise ValueError("Project title cannot be empty")

        # Check if team already has a project for this hackathon
        existing_projects = await zerodb_client.tables.query_rows(
            "projects",
            filter={"hackathon_id": hackathon_id, "team_id": team_id},
            limit=1
        )

        if existing_projects:
            logger.warning(
                f"Team {team_id} already has a project for hackathon {hackathon_id}"
            )
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Team already has a project for this hackathon. "
                "Please update the existing project instead.",
            )

        # Validate team exists
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

        # Generate project ID
        project_id = str(uuid.uuid4())

        # Prepare project data
        project_data = {
            "project_id": project_id,
            "hackathon_id": hackathon_id,
            "team_id": team_id,
            "title": title.strip(),
            "status": "IDEA",
        }

        if one_liner:
            project_data["one_liner"] = one_liner.strip()
        if description:
            project_data["description"] = description.strip()
        if repo_url:
            project_data["repo_url"] = repo_url.strip()
        if demo_url:
            project_data["demo_url"] = demo_url.strip()
        if video_url:
            project_data["video_url"] = video_url.strip()

        # Insert project
        await zerodb_client.tables.insert_rows(
            "projects",
            rows=[project_data]
        )

        logger.info(
            f"Created project {project_id} for team {team_id} "
            f"in hackathon {hackathon_id}"
        )

        # Fetch and return created project
        projects = await zerodb_client.tables.query_rows(
            "projects",
            filter={"project_id": project_id},
            limit=1
        )

        return projects[0]

    except ValueError:
        # Re-raise validation errors
        raise

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout creating project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error creating project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error creating project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project. Please contact support.",
        )


async def get_project(
    zerodb_client: ZeroDBClient,
    project_id: str,
    requester_id: str,
) -> Dict[str, Any]:
    """
    Get project details.

    Args:
        zerodb_client: ZeroDB client instance
        project_id: Project ID to retrieve
        requester_id: User ID making the request (for future authorization)

    Returns:
        Dict with project details

    Raises:
        HTTPException: 404 if project not found
        HTTPException: 500 if database error

    Example:
        >>> project = await get_project(
        ...     client,
        ...     project_id="proj-123",
        ...     requester_id="user-456"
        ... )
        >>> print(project["title"], project["status"])
    """
    try:
        # Get project
        projects = await zerodb_client.tables.query_rows(
            "projects",
            filter={"project_id": project_id},
            limit=1
        )

        if not projects:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        return projects[0]

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout getting project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error getting project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error getting project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project. Please contact support.",
        )


async def list_projects(
    zerodb_client: ZeroDBClient,
    hackathon_id: str,
    requester_id: str,
    status: Optional[ProjectStatus] = None,
    team_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    List projects for a hackathon.

    Args:
        zerodb_client: ZeroDB client instance
        hackathon_id: Hackathon ID to list projects for
        requester_id: User ID making the request (for future authorization)
        status: Optional status filter (IDEA, BUILDING, SUBMITTED)
        team_id: Optional team ID filter
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return (pagination)

    Returns:
        List of project dictionaries

    Raises:
        HTTPException: 500 if database error

    Example:
        >>> projects = await list_projects(
        ...     client,
        ...     hackathon_id="hack-123",
        ...     status="SUBMITTED",
        ...     requester_id="user-456"
        ... )
        >>> print(f"Found {len(projects)} submitted projects")
    """
    try:
        # Build filter
        filter_dict = {"hackathon_id": hackathon_id}
        if status:
            filter_dict["status"] = status
        if team_id:
            filter_dict["team_id"] = team_id

        # Query projects
        projects = await zerodb_client.tables.query_rows(
            "projects",
            filter=filter_dict,
            skip=skip,
            limit=limit
        )

        logger.info(
            f"Listed {len(projects)} projects for hackathon {hackathon_id}"
        )

        return projects

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout listing projects: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error listing projects: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list projects. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error listing projects: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list projects. Please contact support.",
        )


async def update_project(
    zerodb_client: ZeroDBClient,
    project_id: str,
    requester_id: str,
    title: Optional[str] = None,
    one_liner: Optional[str] = None,
    description: Optional[str] = None,
    repo_url: Optional[str] = None,
    demo_url: Optional[str] = None,
    video_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update project details.

    Only team members can update their team's project.

    Args:
        zerodb_client: ZeroDB client instance
        project_id: Project ID to update
        requester_id: User ID making the request (for authorization)
        title: Optional new project title
        one_liner: Optional new short description
        description: Optional new detailed description
        repo_url: Optional new repository URL
        demo_url: Optional new demo URL
        video_url: Optional new video URL

    Returns:
        Dict with updated project details

    Raises:
        ValueError: If title is empty or URLs are invalid
        HTTPException: 404 if project not found
        HTTPException: 403 if requester is not a team member
        HTTPException: 500 if database error

    Example:
        >>> project = await update_project(
        ...     client,
        ...     project_id="proj-123",
        ...     title="Updated Project Title",
        ...     repo_url="https://github.com/user/repo",
        ...     requester_id="user-456"
        ... )
    """
    try:
        # Validate title if provided
        if title is not None and not title.strip():
            raise ValueError("Project title cannot be empty or whitespace")

        # Check if project exists
        projects = await zerodb_client.tables.query_rows(
            "projects",
            filter={"project_id": project_id},
            limit=1
        )

        if not projects:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        project = projects[0]

        # Verify requester is a team member
        team_id = project.get("team_id")
        members = await zerodb_client.tables.query_rows(
            "team_members",
            filter={"team_id": team_id, "participant_id": requester_id},
            limit=1
        )

        if not members:
            logger.warning(
                f"User {requester_id} is not a member of team {team_id}"
            )
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only team members can update the project",
            )

        # Build update data
        update_data = {}
        if title is not None:
            update_data["title"] = title.strip()
        if one_liner is not None:
            update_data["one_liner"] = one_liner.strip()
        if description is not None:
            update_data["description"] = description.strip()
        if repo_url is not None:
            update_data["repo_url"] = repo_url.strip()
        if demo_url is not None:
            update_data["demo_url"] = demo_url.strip()
        if video_url is not None:
            update_data["video_url"] = video_url.strip()

        # Update project
        updated_project = await zerodb_client.tables.update_row(
            "projects",
            project_id,
            data=update_data
        )

        logger.info(f"Updated project {project_id}")

        return updated_project

    except ValueError:
        # Re-raise validation errors
        raise

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout updating project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error updating project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error updating project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project. Please contact support.",
        )


async def update_project_status(
    zerodb_client: ZeroDBClient,
    project_id: str,
    status: ProjectStatus,
    requester_id: str,
) -> Dict[str, Any]:
    """
    Update project status.

    Status transitions: IDEA -> BUILDING -> SUBMITTED
    Only team members can update status.

    Args:
        zerodb_client: ZeroDB client instance
        project_id: Project ID to update
        status: New status (IDEA, BUILDING, SUBMITTED)
        requester_id: User ID making the request (for authorization)

    Returns:
        Dict with updated project details

    Raises:
        ValueError: If status is invalid
        HTTPException: 404 if project not found
        HTTPException: 403 if requester is not a team member
        HTTPException: 500 if database error

    Example:
        >>> project = await update_project_status(
        ...     client,
        ...     project_id="proj-123",
        ...     status="SUBMITTED",
        ...     requester_id="user-456"
        ... )
    """
    try:
        # Validate status
        if status not in ["IDEA", "BUILDING", "SUBMITTED"]:
            raise ValueError(
                f"Invalid status: {status}. "
                "Must be 'IDEA', 'BUILDING', or 'SUBMITTED'"
            )

        # Check if project exists
        projects = await zerodb_client.tables.query_rows(
            "projects",
            filter={"project_id": project_id},
            limit=1
        )

        if not projects:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        project = projects[0]

        # Verify requester is a team member
        team_id = project.get("team_id")
        members = await zerodb_client.tables.query_rows(
            "team_members",
            filter={"team_id": team_id, "participant_id": requester_id},
            limit=1
        )

        if not members:
            logger.warning(
                f"User {requester_id} is not a member of team {team_id}"
            )
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only team members can update the project status",
            )

        # Update status
        updated_project = await zerodb_client.tables.update_row(
            "projects",
            project_id,
            data={"status": status}
        )

        logger.info(f"Updated project {project_id} status to {status}")

        return updated_project

    except ValueError:
        # Re-raise validation errors
        raise

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout updating project status: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error updating project status: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project status. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error updating project status: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project status. Please contact support.",
        )


async def delete_project(
    zerodb_client: ZeroDBClient,
    project_id: str,
    requester_id: str,
) -> Dict[str, Any]:
    """
    Delete a project.

    Only team members can delete their team's project.

    Args:
        zerodb_client: ZeroDB client instance
        project_id: Project ID to delete
        requester_id: User ID making the request (for authorization)

    Returns:
        Dict with success status

    Raises:
        HTTPException: 404 if project not found
        HTTPException: 403 if requester is not a team member
        HTTPException: 500 if database error

    Example:
        >>> result = await delete_project(
        ...     client,
        ...     project_id="proj-123",
        ...     requester_id="user-456"
        ... )
    """
    try:
        # Check if project exists
        projects = await zerodb_client.tables.query_rows(
            "projects",
            filter={"project_id": project_id},
            limit=1
        )

        if not projects:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        project = projects[0]

        # Verify requester is a team member
        team_id = project.get("team_id")
        members = await zerodb_client.tables.query_rows(
            "team_members",
            filter={"team_id": team_id, "participant_id": requester_id},
            limit=1
        )

        if not members:
            logger.warning(
                f"User {requester_id} is not a member of team {team_id}"
            )
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only team members can delete the project",
            )

        # Delete project
        await zerodb_client.tables.delete_row("projects", project_id)

        logger.info(f"Deleted project {project_id}")

        return {"success": True}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout deleting project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error deleting project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project. Please contact support.",
        )

    except Exception as e:
        logger.error(f"Unexpected error deleting project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project. Please contact support.",
        )


async def get_team_project(
    zerodb_client: ZeroDBClient,
    team_id: str,
    requester_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get a team's project (if any).

    Args:
        zerodb_client: ZeroDB client instance
        team_id: Team ID to get project for
        requester_id: User ID making the request (for future authorization)

    Returns:
        Dict with project details or None if no project exists

    Raises:
        HTTPException: 500 if database error

    Example:
        >>> project = await get_team_project(
        ...     client,
        ...     team_id="team-123",
        ...     requester_id="user-456"
        ... )
        >>> if project:
        ...     print(project["title"])
    """
    try:
        # Get team's project
        projects = await zerodb_client.tables.query_rows(
            "projects",
            filter={"team_id": team_id},
            limit=1
        )

        if not projects:
            return None

        return projects[0]

    except ZeroDBTimeoutError as e:
        logger.error(f"Timeout getting team project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timed out. Please try again.",
        )

    except (ZeroDBError, ZeroDBNotFound) as e:
        logger.error(f"Database error getting team project: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team project. Please contact support.",
        )

    except Exception as e:
        logger.error(
            f"Unexpected error getting team project: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team project. Please contact support.",
        )
