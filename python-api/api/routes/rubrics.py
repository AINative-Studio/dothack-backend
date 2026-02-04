"""
Rubrics API Routes

RESTful API endpoints for judging rubrics management.
Rubrics define evaluation criteria for hackathon projects.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_zerodb_client
from api.schemas.rubric import (
    ErrorResponse,
    RubricActivateRequest,
    RubricCreateRequest,
    RubricListResponse,
    RubricResponse,
    RubricUpdateRequest,
)
from integrations.zerodb.client import ZeroDBClient
from services import rubric_service


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/hackathons",
    tags=["Rubrics"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - ORGANIZER required"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.post(
    "/{hackathon_id}/rubrics",
    response_model=RubricResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create rubric",
    description="""
    Create a new judging rubric for a hackathon.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon

    Rubrics define evaluation criteria with weights that must sum to 1.0.
    Optionally set as active rubric immediately upon creation.
    """,
)
async def create_rubric(
    hackathon_id: str,
    request: RubricCreateRequest,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> RubricResponse:
    """Create a new rubric."""
    logger.info(
        f"User {current_user['id']} creating rubric '{request.name}' "
        f"for hackathon {hackathon_id}"
    )

    rubric = await rubric_service.create_rubric(
        zerodb_client=zerodb,
        hackathon_id=hackathon_id,
        user_id=current_user["id"],
        name=request.name,
        criteria=[criterion.model_dump() for criterion in request.criteria],
        is_active=request.is_active,
    )

    return RubricResponse(**rubric)


@router.get(
    "/{hackathon_id}/rubrics",
    response_model=RubricListResponse,
    summary="List rubrics",
    description="""
    List all rubrics for a hackathon.

    **Authentication Required:** Yes
    **Permissions:** Any authenticated user
    """,
)
async def list_rubrics(
    hackathon_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> RubricListResponse:
    """List all rubrics for a hackathon."""
    logger.info(f"User {current_user['id']} listing rubrics for hackathon {hackathon_id}")

    result = await rubric_service.list_rubrics(zerodb, hackathon_id)

    return RubricListResponse(
        rubrics=[RubricResponse(**rubric) for rubric in result["rubrics"]],
        total=result["total"],
        hackathon_id=hackathon_id,
    )


@router.get(
    "/{hackathon_id}/rubrics/active",
    response_model=RubricResponse,
    summary="Get active rubric",
    description="""
    Get the currently active rubric for a hackathon.

    **Authentication Required:** Yes
    **Permissions:** Any authenticated user (JUDGE, ORGANIZER, etc.)
    """,
)
async def get_active_rubric(
    hackathon_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> RubricResponse:
    """Get the active rubric for judging."""
    logger.info(f"User {current_user['id']} retrieving active rubric for hackathon {hackathon_id}")

    rubric = await rubric_service.get_active_rubric(zerodb, hackathon_id)

    return RubricResponse(**rubric)


@router.get(
    "/{hackathon_id}/rubrics/{rubric_id}",
    response_model=RubricResponse,
    summary="Get rubric",
    description="""
    Get a single rubric by ID.

    **Authentication Required:** Yes
    **Permissions:** Any authenticated user
    """,
)
async def get_rubric(
    hackathon_id: str,
    rubric_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> RubricResponse:
    """Get a single rubric."""
    logger.info(f"User {current_user['id']} retrieving rubric {rubric_id}")

    rubric = await rubric_service.get_rubric(zerodb, hackathon_id, rubric_id)

    return RubricResponse(**rubric)


@router.put(
    "/{hackathon_id}/rubrics/{rubric_id}",
    response_model=RubricResponse,
    summary="Update rubric",
    description="""
    Update a rubric's details.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon
    """,
)
async def update_rubric(
    hackathon_id: str,
    rubric_id: str,
    request: RubricUpdateRequest,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> RubricResponse:
    """Update a rubric."""
    logger.info(f"User {current_user['id']} updating rubric {rubric_id}")

    # Build update dict
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}

    if not update_data:
        rubric = await rubric_service.get_rubric(zerodb, hackathon_id, rubric_id)
        return RubricResponse(**rubric)

    # Convert criteria to list of dicts if present
    if "criteria" in update_data:
        update_data["criteria"] = [
            criterion.model_dump() for criterion in request.criteria
        ]

    rubric = await rubric_service.update_rubric(
        zerodb_client=zerodb,
        hackathon_id=hackathon_id,
        rubric_id=rubric_id,
        user_id=current_user["id"],
        update_data=update_data,
    )

    return RubricResponse(**rubric)


@router.patch(
    "/{hackathon_id}/rubrics/{rubric_id}/activate",
    response_model=RubricResponse,
    summary="Activate rubric",
    description="""
    Set a rubric as the active rubric for judging.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon

    Only one rubric can be active at a time. Setting a rubric as active
    will deactivate any previously active rubric.
    """,
)
async def activate_rubric(
    hackathon_id: str,
    rubric_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> RubricResponse:
    """Activate a rubric for judging."""
    logger.info(
        f"User {current_user['id']} activating rubric {rubric_id} "
        f"for hackathon {hackathon_id}"
    )

    rubric = await rubric_service.activate_rubric(
        zerodb_client=zerodb,
        hackathon_id=hackathon_id,
        rubric_id=rubric_id,
        user_id=current_user["id"],
    )

    return RubricResponse(**rubric)


@router.delete(
    "/{hackathon_id}/rubrics/{rubric_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete rubric",
    description="""
    Delete a rubric.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon

    Cannot delete the active rubric - deactivate it first.
    """,
)
async def delete_rubric(
    hackathon_id: str,
    rubric_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> None:
    """Delete a rubric."""
    logger.info(f"User {current_user['id']} deleting rubric {rubric_id}")

    await rubric_service.delete_rubric(
        zerodb_client=zerodb,
        hackathon_id=hackathon_id,
        rubric_id=rubric_id,
        user_id=current_user["id"],
    )

    return None
