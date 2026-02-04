"""
Featured Hackathons API Routes

RESTful API endpoints for managing featured hackathons on the homepage.
Public read access, admin-only write access.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_zerodb_client, require_admin
from api.schemas.featured_hackathon import (
    ErrorResponse,
    FeaturedHackathonCreateRequest,
    FeaturedHackathonListResponse,
    FeaturedHackathonResponse,
    FeaturedHackathonUpdateRequest,
)
from integrations.zerodb.client import ZeroDBClient
from services import featured_hackathon_service


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/featured-hackathons",
    tags=["Featured Hackathons"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Admin only"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.get(
    "",
    response_model=FeaturedHackathonListResponse,
    summary="List featured hackathons (PUBLIC)",
    description="""
    List all featured hackathons for homepage display.

    **Authentication Required:** NO (public endpoint)
    **Permissions:** Public read access

    Returns active featured hackathons sorted by display_order.
    """,
)
async def list_featured_hackathons(
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> FeaturedHackathonListResponse:
    """List all featured hackathons (public)."""
    logger.info("Public user listing featured hackathons")

    result = await featured_hackathon_service.list_featured(zerodb)

    return FeaturedHackathonListResponse(
        featured_hackathons=[
            FeaturedHackathonResponse(**fh) for fh in result["featured_hackathons"]
        ],
        total=result["total"],
    )


@router.get(
    "/{featured_id}",
    response_model=FeaturedHackathonResponse,
    summary="Get featured hackathon (PUBLIC)",
    description="""
    Get a single featured hackathon by ID.

    **Authentication Required:** NO (public endpoint)
    **Permissions:** Public read access
    """,
)
async def get_featured_hackathon(
    featured_id: str,
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> FeaturedHackathonResponse:
    """Get a single featured hackathon (public)."""
    logger.info(f"Public user retrieving featured hackathon {featured_id}")

    featured = await featured_hackathon_service.get_featured(featured_id, zerodb)

    return FeaturedHackathonResponse(**featured)


@router.post(
    "",
    response_model=FeaturedHackathonResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Create featured hackathon (ADMIN)",
    description="""
    Add a hackathon to featured list.

    **Authentication Required:** Yes
    **Permissions:** ADMIN role only
    """,
)
async def create_featured_hackathon(
    request: FeaturedHackathonCreateRequest,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> FeaturedHackathonResponse:
    """Create a featured hackathon entry (admin only)."""
    logger.info(
        f"Admin {current_user['id']} featuring hackathon {request.hackathon_id}"
    )

    featured = await featured_hackathon_service.create_featured(
        zerodb=zerodb,
        hackathon_id=request.hackathon_id,
        display_order=request.display_order,
        featured_until=request.featured_until,
    )

    return FeaturedHackathonResponse(**featured)


@router.put(
    "/{featured_id}",
    response_model=FeaturedHackathonResponse,
    dependencies=[Depends(require_admin)],
    summary="Update featured hackathon (ADMIN)",
    description="""
    Update featured hackathon details.

    **Authentication Required:** Yes
    **Permissions:** ADMIN role only
    """,
)
async def update_featured_hackathon(
    featured_id: str,
    request: FeaturedHackathonUpdateRequest,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> FeaturedHackathonResponse:
    """Update a featured hackathon (admin only)."""
    logger.info(f"Admin {current_user['id']} updating featured hackathon {featured_id}")

    # Build update dict
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}

    if not update_data:
        featured = await featured_hackathon_service.get_featured(featured_id, zerodb)
        return FeaturedHackathonResponse(**featured)

    featured = await featured_hackathon_service.update_featured(
        zerodb=zerodb,
        featured_id=featured_id,
        update_data=update_data,
    )

    return FeaturedHackathonResponse(**featured)


@router.patch(
    "/{featured_id}/order",
    response_model=FeaturedHackathonResponse,
    dependencies=[Depends(require_admin)],
    summary="Update display order (ADMIN)",
    description="""
    Update the display order of a featured hackathon.

    **Authentication Required:** Yes
    **Permissions:** ADMIN role only
    """,
)
async def update_display_order(
    featured_id: str,
    display_order: int,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> FeaturedHackathonResponse:
    """Update display order (admin only)."""
    logger.info(
        f"Admin {current_user['id']} updating display order "
        f"for featured hackathon {featured_id} to {display_order}"
    )

    featured = await featured_hackathon_service.update_featured(
        zerodb=zerodb,
        featured_id=featured_id,
        update_data={"display_order": display_order},
    )

    return FeaturedHackathonResponse(**featured)


@router.delete(
    "/{featured_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
    summary="Remove from featured (ADMIN)",
    description="""
    Remove a hackathon from the featured list.

    **Authentication Required:** Yes
    **Permissions:** ADMIN role only
    """,
)
async def delete_featured_hackathon(
    featured_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> None:
    """Remove from featured list (admin only)."""
    logger.info(
        f"Admin {current_user['id']} removing featured hackathon {featured_id}"
    )

    await featured_hackathon_service.delete_featured(zerodb, featured_id)

    return None
