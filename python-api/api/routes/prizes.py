"""
Prize API Routes

RESTful API endpoints for hackathon prize CRUD operations.
"""

import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from api.dependencies import get_current_user, get_zerodb_client
from api.schemas.prize import (
    ErrorResponse,
    PrizeCreateRequest,
    PrizeListResponse,
    PrizeResponse,
    PrizeUpdateRequest,
)
from integrations.zerodb.client import ZeroDBClient
from services.authorization import check_organizer
from services.prize_service import PrizeService


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/hackathons",
    tags=["Prizes"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.post(
    "/{hackathon_id}/prizes",
    response_model=PrizeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a prize",
    description="""
    Create a new prize for a hackathon.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon

    Prizes can be hackathon-level (overall winners) or track-specific.
    Rank must be unique within the same scope (hackathon or track).
    """,
)
async def create_prize(
    hackathon_id: str,
    request: PrizeCreateRequest,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> PrizeResponse:
    """
    Create a new prize.

    Args:
        hackathon_id: UUID of the hackathon
        request: Prize creation data
        current_user: Authenticated user
        zerodb: ZeroDB client

    Returns:
        Created prize data

    Raises:
        403: If user is not an ORGANIZER
        404: If hackathon or track not found
        409: If rank already exists for the same scope
    """
    # Verify user is organizer
    await check_organizer(zerodb, current_user["id"], hackathon_id)

    logger.info(
        f"User {current_user['id']} creating prize '{request.title}' "
        f"for hackathon {hackathon_id}"
    )

    service = PrizeService(zerodb)
    prize = await service.create_prize(
        hackathon_id=hackathon_id,
        title=request.title,
        description=request.description,
        amount=request.amount,
        currency=request.currency,
        rank=request.rank,
        track_id=request.track_id,
        sponsor_name=request.sponsor_name,
        display_order=request.display_order,
    )

    return PrizeResponse(**prize)


@router.get(
    "/{hackathon_id}/prizes",
    response_model=PrizeListResponse,
    summary="List prizes",
    description="""
    List all prizes for a hackathon.

    **Authentication Required:** No (public endpoint)
    **Permissions:** Any user can view prizes

    Supports filtering by track_id and rank.
    Results are sorted by display_order and rank.
    """,
)
async def list_prizes(
    hackathon_id: str,
    track_id: Optional[str] = Query(None, description="Filter by track ID"),
    rank: Optional[int] = Query(None, ge=1, le=100, description="Filter by rank"),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> PrizeListResponse:
    """
    List all prizes for a hackathon.

    Args:
        hackathon_id: UUID of the hackathon
        track_id: Optional filter by track ID
        rank: Optional filter by rank
        zerodb: ZeroDB client

    Returns:
        List of prizes with total count and prize pool summary
    """
    logger.info(f"Listing prizes for hackathon {hackathon_id}")

    service = PrizeService(zerodb)
    result = await service.list_prizes(
        hackathon_id=hackathon_id,
        track_id=track_id,
        rank=rank,
    )

    prize_models = []
    for prize in result["prizes"]:
        try:
            prize_models.append(PrizeResponse(**prize))
        except (ValidationError, Exception) as e:
            logger.warning(f"Skipping prize with invalid data: {e}")
            continue

    return PrizeListResponse(
        prizes=prize_models,
        total=len(prize_models),
        hackathon_id=result["hackathon_id"],
        total_prize_pool=result.get("total_prize_pool"),
    )


@router.get(
    "/{hackathon_id}/prizes/{prize_id}",
    response_model=PrizeResponse,
    summary="Get prize",
    description="""
    Get a single prize by ID.

    **Authentication Required:** No (public endpoint)
    **Permissions:** Any user can view prizes
    """,
)
async def get_prize(
    hackathon_id: str,
    prize_id: str,
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> PrizeResponse:
    """
    Get a single prize.

    Args:
        hackathon_id: UUID of the hackathon
        prize_id: UUID of the prize
        zerodb: ZeroDB client

    Returns:
        Prize data

    Raises:
        404: If prize not found
    """
    logger.info(f"Retrieving prize {prize_id}")

    service = PrizeService(zerodb)
    prize = await service.get_prize(hackathon_id, prize_id)

    return PrizeResponse(**prize)


@router.put(
    "/{hackathon_id}/prizes/{prize_id}",
    response_model=PrizeResponse,
    summary="Update prize",
    description="""
    Update a prize's details.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon

    Only provided fields will be updated.
    Rank must remain unique within the same scope.
    """,
)
async def update_prize(
    hackathon_id: str,
    prize_id: str,
    request: PrizeUpdateRequest,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> PrizeResponse:
    """
    Update a prize.

    Args:
        hackathon_id: UUID of the hackathon
        prize_id: UUID of the prize
        request: Prize update data
        current_user: Authenticated user
        zerodb: ZeroDB client

    Returns:
        Updated prize data

    Raises:
        403: If user is not an ORGANIZER
        404: If prize or track not found
        409: If rank conflicts
    """
    # Verify user is organizer
    await check_organizer(zerodb, current_user["id"], hackathon_id)

    logger.info(f"User {current_user['id']} updating prize {prize_id}")

    # Build update dict (only include non-None fields)
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}

    if not update_data:
        # No fields to update, return current prize
        service = PrizeService(zerodb)
        prize = await service.get_prize(hackathon_id, prize_id)
        return PrizeResponse(**prize)

    service = PrizeService(zerodb)
    prize = await service.update_prize(
        hackathon_id=hackathon_id,
        prize_id=prize_id,
        update_data=update_data,
    )

    return PrizeResponse(**prize)


@router.delete(
    "/{hackathon_id}/prizes/{prize_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete prize",
    description="""
    Delete a prize.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon

    This is a hard delete operation and cannot be undone.
    """,
)
async def delete_prize(
    hackathon_id: str,
    prize_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> None:
    """
    Delete a prize.

    Args:
        hackathon_id: UUID of the hackathon
        prize_id: UUID of the prize
        current_user: Authenticated user
        zerodb: ZeroDB client

    Raises:
        403: If user is not an ORGANIZER
        404: If prize not found
    """
    # Verify user is organizer
    await check_organizer(zerodb, current_user["id"], hackathon_id)

    logger.info(f"User {current_user['id']} deleting prize {prize_id}")

    service = PrizeService(zerodb)
    await service.delete_prize(hackathon_id, prize_id)

    return None
