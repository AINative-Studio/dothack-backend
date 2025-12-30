"""
Project service for managing hackathon projects.

Handles CRUD operations, status transitions, and authorization for projects.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status

from api.schemas.project import ProjectStatus
from integrations.zerodb.client import ZeroDBClient


logger = logging.getLogger(__name__)


# Status transition rules
STATUS_TRANSITIONS = {
    "IDEA": ["BUILDING"],
    "BUILDING": ["SUBMITTED"],
    "SUBMITTED": []  # Terminal state
}


async def verify_hackathon_exists(
    hackathon_id: str,
    zerodb: ZeroDBClient
) -> None:
    """
    Verify that a hackathon exists.

    Args:
        hackathon_id: UUID of the hackathon
        zerodb: ZeroDB client instance

    Raises:
        HTTPException: If hackathon not found or database error
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="hackathons",
            filter={"hackathon_id": hackathon_id},
            limit=1
        )

        if not response or not response.get("rows"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hackathon {hackathon_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying hackathon existence: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify hackathon: {str(e)}"
        )


async def verify_team_exists(
    team_id: str,
    hackathon_id: str,
    zerodb: ZeroDBClient
) -> None:
    """
    Verify that a team exists and belongs to the hackathon.

    Args:
        team_id: UUID of the team
        hackathon_id: UUID of the hackathon
        zerodb: ZeroDB client instance

    Raises:
        HTTPException: If team not found or doesn't belong to hackathon
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="teams",
            filter={
                "team_id": team_id,
                "hackathon_id": hackathon_id
            },
            limit=1
        )

        if not response or not response.get("rows"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team {team_id} not found in hackathon {hackathon_id}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying team existence: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify team: {str(e)}"
        )


async def check_existing_project(
    team_id: str,
    hackathon_id: str,
    zerodb: ZeroDBClient,
    exclude_project_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Check if team already has a project in the hackathon.

    Args:
        team_id: UUID of the team
        hackathon_id: UUID of the hackathon
        zerodb: ZeroDB client instance
        exclude_project_id: Project ID to exclude from check (for updates)

    Returns:
        Existing project dict if found, None otherwise

    Raises:
        HTTPException: If database error occurs
    """
    try:
        filter_dict = {
            "team_id": team_id,
            "hackathon_id": hackathon_id
        }

        response = await zerodb.tables.query_rows(
            table_id="projects",
            filter=filter_dict,
            limit=10  # Should only be 1, but query a few to be safe
        )

        if response and response.get("rows"):
            for project in response["rows"]:
                if exclude_project_id and project.get("project_id") == exclude_project_id:
                    continue
                return project

        return None

    except Exception as e:
        logger.error(f"Error checking existing project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check existing project: {str(e)}"
        )


async def validate_status_transition(
    current_status: str,
    new_status: str
) -> None:
    """
    Validate that a status transition is allowed.

    Args:
        current_status: Current project status
        new_status: Desired new status

    Raises:
        HTTPException: If transition is not allowed
    """
    if current_status not in STATUS_TRANSITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid current status: {current_status}"
        )

    allowed_transitions = STATUS_TRANSITIONS[current_status]

    if new_status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {current_status} to {new_status}. "
                   f"Allowed transitions: {', '.join(allowed_transitions) if allowed_transitions else 'none (terminal state)'}"
        )


async def create_project(
    hackathon_id: str,
    team_id: str,
    title: str,
    one_liner: Optional[str],
    repo_url: Optional[str],
    demo_url: Optional[str],
    zerodb: ZeroDBClient
) -> Dict:
    """
    Create a new project for a team.

    Args:
        hackathon_id: UUID of the hackathon
        team_id: UUID of the team
        title: Project title
        one_liner: Short description
        repo_url: Repository URL
        demo_url: Demo URL
        zerodb: ZeroDB client instance

    Returns:
        Created project data

    Raises:
        HTTPException: If validation fails or database error
    """
    # Verify hackathon exists
    await verify_hackathon_exists(hackathon_id, zerodb)

    # Verify team exists and belongs to hackathon
    await verify_team_exists(team_id, hackathon_id, zerodb)

    # Check if team already has a project in this hackathon
    existing = await check_existing_project(team_id, hackathon_id, zerodb)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Team {team_id} already has a project in hackathon {hackathon_id}"
        )

    try:
        project_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        project_data = {
            "project_id": project_id,
            "hackathon_id": hackathon_id,
            "team_id": team_id,
            "title": title,
            "one_liner": one_liner,
            "status": "IDEA",
            "repo_url": repo_url,
            "demo_url": demo_url,
            "created_at": now,
            "updated_at": now
        }

        await zerodb.tables.insert_rows(
            table_id="projects",
            rows=[project_data]
        )

        logger.info(f"Created project {project_id} for team {team_id}")
        return project_data

    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


async def get_project(
    project_id: str,
    zerodb: ZeroDBClient
) -> Dict:
    """
    Get a project by ID.

    Args:
        project_id: UUID of the project
        zerodb: ZeroDB client instance

    Returns:
        Project data

    Raises:
        HTTPException: If project not found or database error
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="projects",
            filter={"project_id": project_id},
            limit=1
        )

        if not response or not response.get("rows"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        return response["rows"][0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project: {str(e)}"
        )


async def list_projects(
    hackathon_id: str,
    status_filter: Optional[str],
    skip: int,
    limit: int,
    zerodb: ZeroDBClient
) -> Dict:
    """
    List projects for a hackathon with optional filtering.

    Args:
        hackathon_id: UUID of the hackathon
        status_filter: Optional status to filter by
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        zerodb: ZeroDB client instance

    Returns:
        Dict with projects list and total count

    Raises:
        HTTPException: If database error occurs
    """
    try:
        filter_dict = {"hackathon_id": hackathon_id}
        if status_filter:
            filter_dict["status"] = status_filter

        response = await zerodb.tables.query_rows(
            table_id="projects",
            filter=filter_dict,
            limit=limit + skip  # Get more to handle pagination
        )

        projects = response.get("rows", [])
        total = len(projects)

        # Apply pagination
        paginated_projects = projects[skip:skip + limit]

        return {
            "projects": paginated_projects,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


async def get_team_project(
    team_id: str,
    hackathon_id: str,
    zerodb: ZeroDBClient
) -> Optional[Dict]:
    """
    Get a team's project in a specific hackathon.

    Args:
        team_id: UUID of the team
        hackathon_id: UUID of the hackathon
        zerodb: ZeroDB client instance

    Returns:
        Project data if found, None otherwise

    Raises:
        HTTPException: If database error occurs
    """
    try:
        response = await zerodb.tables.query_rows(
            table_id="projects",
            filter={
                "team_id": team_id,
                "hackathon_id": hackathon_id
            },
            limit=1
        )

        if response and response.get("rows"):
            return response["rows"][0]
        return None

    except Exception as e:
        logger.error(f"Error retrieving team project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve team project: {str(e)}"
        )


async def update_project(
    project_id: str,
    update_data: Dict,
    zerodb: ZeroDBClient
) -> Dict:
    """
    Update a project's details.

    Args:
        project_id: UUID of the project
        update_data: Dict of fields to update
        zerodb: ZeroDB client instance

    Returns:
        Updated project data

    Raises:
        HTTPException: If project not found or database error
    """
    # Get current project
    project = await get_project(project_id, zerodb)

    try:
        # Merge updates
        update_data["updated_at"] = datetime.utcnow().isoformat()
        project.update(update_data)

        # Update in database
        await zerodb.tables.update_rows(
            table_id="projects",
            filter={"project_id": project_id},
            update={"$set": update_data}
        )

        logger.info(f"Updated project {project_id}")
        return project

    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


async def update_project_status(
    project_id: str,
    new_status: str,
    zerodb: ZeroDBClient
) -> Dict:
    """
    Update a project's status with validation.

    Args:
        project_id: UUID of the project
        new_status: New status (IDEA, BUILDING, or SUBMITTED)
        zerodb: ZeroDB client instance

    Returns:
        Updated project data

    Raises:
        HTTPException: If transition invalid or database error
    """
    # Get current project
    project = await get_project(project_id, zerodb)

    current_status = project.get("status")

    # Validate transition
    await validate_status_transition(current_status, new_status)

    # Update status
    return await update_project(
        project_id,
        {"status": new_status},
        zerodb
    )


async def delete_project(
    project_id: str,
    zerodb: ZeroDBClient
) -> None:
    """
    Delete a project.

    Args:
        project_id: UUID of the project
        zerodb: ZeroDB client instance

    Raises:
        HTTPException: If project not found or database error
    """
    # Verify project exists
    await get_project(project_id, zerodb)

    try:
        await zerodb.tables.delete_rows(
            table_id="projects",
            filter={"project_id": project_id}
        )

        logger.info(f"Deleted project {project_id}")

    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )
