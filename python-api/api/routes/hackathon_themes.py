"""
API routes for hackathon theme management.

Provides public endpoints for theme listing and protected admin endpoints for CRUD.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_zerodb_client, require_admin
from api.schemas.hackathon_theme import (
    ErrorResponse,
    HackathonThemeCreateRequest,
    HackathonThemeListResponse,
    HackathonThemeOrderUpdateRequest,
    HackathonThemeResponse,
    HackathonThemeUpdateRequest,
)
from integrations.zerodb.client import ZeroDBClient
from services import hackathon_theme_service


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1", tags=["hackathon-themes"])


@router.get(
    "/hackathon-themes",
    response_model=HackathonThemeListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_hackathon_themes(
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    List all hackathon themes with statistics (PUBLIC).

    No authentication required - this endpoint is public for homepage display.

    Returns themes ordered by display_order with:
    - Theme name and description
    - Icon emoji
    - Number of hackathons
    - Total prize pool
    """
    logger.info("Listing all hackathon themes (public)")

    result = await hackathon_theme_service.list_themes(zerodb)

    return HackathonThemeListResponse(
        themes=[HackathonThemeResponse(**theme) for theme in result["themes"]],
        total=result["total"]
    )


@router.get(
    "/hackathon-themes/{theme_id}",
    response_model=HackathonThemeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Theme not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_hackathon_theme(
    theme_id: str,
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Get a single hackathon theme by ID (PUBLIC).

    No authentication required.
    """
    logger.info(f"Retrieving hackathon theme {theme_id} (public)")

    theme = await hackathon_theme_service.get_theme(theme_id, zerodb)

    return HackathonThemeResponse(**theme)


@router.post(
    "/hackathon-themes",
    response_model=HackathonThemeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized (admin only)"},
        409: {"model": ErrorResponse, "description": "Theme name already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_hackathon_theme(
    request: HackathonThemeCreateRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Create a new hackathon theme (ADMIN ONLY).

    Creates a new theme category with optional icon and description.
    Display order is auto-assigned if not provided.

    **Authorization:** Requires ADMIN role
    """
    logger.info(f"Admin {current_user.get('user_id')} creating theme: {request.theme_name}")

    theme = await hackathon_theme_service.create_theme(
        theme_name=request.theme_name,
        description=request.description,
        icon=request.icon,
        display_order=request.display_order,
        zerodb=zerodb
    )

    return HackathonThemeResponse(**theme)


@router.put(
    "/hackathon-themes/{theme_id}",
    response_model=HackathonThemeResponse,
    dependencies=[Depends(require_admin)],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized (admin only)"},
        404: {"model": ErrorResponse, "description": "Theme not found"},
        409: {"model": ErrorResponse, "description": "Theme name already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_hackathon_theme(
    theme_id: str,
    request: HackathonThemeUpdateRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Update a hackathon theme's details (ADMIN ONLY).

    Updates theme name, description, icon, or display order.
    Only provided fields will be updated.

    **Authorization:** Requires ADMIN role
    """
    logger.info(f"Admin {current_user.get('user_id')} updating theme {theme_id}")

    # Build update dict (only include non-None fields)
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}

    if not update_data:
        # No fields to update, return current theme
        theme = await hackathon_theme_service.get_theme(theme_id, zerodb)
        return HackathonThemeResponse(**theme)

    # Update theme
    updated_theme = await hackathon_theme_service.update_theme(
        theme_id, update_data, zerodb
    )

    return HackathonThemeResponse(**updated_theme)


@router.patch(
    "/hackathon-themes/{theme_id}/order",
    response_model=HackathonThemeResponse,
    dependencies=[Depends(require_admin)],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid display order"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized (admin only)"},
        404: {"model": ErrorResponse, "description": "Theme not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_theme_display_order(
    theme_id: str,
    request: HackathonThemeOrderUpdateRequest,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Update a theme's display order (ADMIN ONLY).

    Changes the order in which themes appear on the homepage.

    **Authorization:** Requires ADMIN role
    """
    logger.info(
        f"Admin {current_user.get('user_id')} updating theme {theme_id} order to {request.display_order}"
    )

    updated_theme = await hackathon_theme_service.update_theme_order(
        theme_id, request.display_order, zerodb
    )

    return HackathonThemeResponse(**updated_theme)


@router.delete(
    "/hackathon-themes/{theme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized (admin only)"},
        404: {"model": ErrorResponse, "description": "Theme not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_hackathon_theme(
    theme_id: str,
    current_user: dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
):
    """
    Delete a hackathon theme (ADMIN ONLY).

    Removes a theme category. Use with caution.

    **Authorization:** Requires ADMIN role
    """
    logger.info(f"Admin {current_user.get('user_id')} deleting theme {theme_id}")

    await hackathon_theme_service.delete_theme(theme_id, zerodb)

    return None
