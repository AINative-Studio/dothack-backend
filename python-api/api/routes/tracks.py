"""
Track API Routes

RESTful API endpoints for hackathon track CRUD operations.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user, get_zerodb_client
from api.schemas.track import (
    ErrorResponse,
    TrackCreateRequest,
    TrackListResponse,
    TrackResponse,
    TrackUpdateRequest,
)
from integrations.zerodb.client import ZeroDBClient
from services import track_service
from services.authorization import check_organizer


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/hackathons",
    tags=["Tracks"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.post(
    "/{hackathon_id}/tracks",
    response_model=TrackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a track",
    description="""
    Create a new track for a hackathon.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon

    Track names must be unique within a hackathon.
    """,
)
async def create_track(
    hackathon_id: str,
    request: TrackCreateRequest,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> TrackResponse:
    """
    Create a new track.

    Args:
        hackathon_id: UUID of the hackathon
        request: Track creation data
        current_user: Authenticated user
        zerodb: ZeroDB client

    Returns:
        Created track data

    Raises:
        403: If user is not an ORGANIZER
        409: If track name already exists
    """
    # Verify user is organizer
    await check_organizer(zerodb, current_user["id"], hackathon_id)

    logger.info(
        f"User {current_user['id']} creating track '{request.name}' "
        f"for hackathon {hackathon_id}"
    )

    track = await track_service.create_track(
        hackathon_id=hackathon_id,
        name=request.name,
        description=request.description,
        zerodb=zerodb,
    )

    return TrackResponse(**track)


@router.get(
    "/{hackathon_id}/tracks",
    response_model=TrackListResponse,
    summary="List tracks",
    description="""
    List all tracks for a hackathon.

    **Authentication Required:** Yes
    **Permissions:** Any authenticated user
    """,
)
async def list_tracks(
    hackathon_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> TrackListResponse:
    """
    List all tracks for a hackathon.

    Args:
        hackathon_id: UUID of the hackathon
        current_user: Authenticated user
        zerodb: ZeroDB client

    Returns:
        List of tracks with total count
    """
    logger.info(f"User {current_user['id']} listing tracks for hackathon {hackathon_id}")

    result = await track_service.list_tracks(hackathon_id, zerodb)

    return TrackListResponse(
        tracks=[TrackResponse(**track) for track in result["tracks"]],
        total=result["total"],
        hackathon_id=hackathon_id,
    )


@router.get(
    "/{hackathon_id}/tracks/{track_id}",
    response_model=TrackResponse,
    summary="Get track",
    description="""
    Get a single track by ID.

    **Authentication Required:** Yes
    **Permissions:** Any authenticated user
    """,
)
async def get_track(
    hackathon_id: str,
    track_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> TrackResponse:
    """
    Get a single track.

    Args:
        hackathon_id: UUID of the hackathon
        track_id: UUID of the track
        current_user: Authenticated user
        zerodb: ZeroDB client

    Returns:
        Track data

    Raises:
        404: If track not found
    """
    logger.info(f"User {current_user['id']} retrieving track {track_id}")

    track = await track_service.get_track(hackathon_id, track_id, zerodb)

    return TrackResponse(**track)


@router.put(
    "/{hackathon_id}/tracks/{track_id}",
    response_model=TrackResponse,
    summary="Update track",
    description="""
    Update a track's details.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon
    """,
)
async def update_track(
    hackathon_id: str,
    track_id: str,
    request: TrackUpdateRequest,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> TrackResponse:
    """
    Update a track.

    Args:
        hackathon_id: UUID of the hackathon
        track_id: UUID of the track
        request: Track update data
        current_user: Authenticated user
        zerodb: ZeroDB client

    Returns:
        Updated track data

    Raises:
        403: If user is not an ORGANIZER
        404: If track not found
        409: If name conflicts
    """
    # Verify user is organizer
    await check_organizer(zerodb, current_user["id"], hackathon_id)

    logger.info(f"User {current_user['id']} updating track {track_id}")

    # Build update dict (only include non-None fields)
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}

    if not update_data:
        # No fields to update, return current track
        track = await track_service.get_track(hackathon_id, track_id, zerodb)
        return TrackResponse(**track)

    track = await track_service.update_track(
        hackathon_id=hackathon_id,
        track_id=track_id,
        update_data=update_data,
        zerodb=zerodb,
    )

    return TrackResponse(**track)


@router.delete(
    "/{hackathon_id}/tracks/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete track",
    description="""
    Delete a track.

    **Authentication Required:** Yes
    **Permissions:** ORGANIZER role for the hackathon

    Cannot delete a track that has teams assigned to it.
    """,
)
async def delete_track(
    hackathon_id: str,
    track_id: str,
    current_user: Dict = Depends(get_current_user),
    zerodb: ZeroDBClient = Depends(get_zerodb_client),
) -> None:
    """
    Delete a track.

    Args:
        hackathon_id: UUID of the hackathon
        track_id: UUID of the track
        current_user: Authenticated user
        zerodb: ZeroDB client

    Raises:
        403: If user is not an ORGANIZER
        404: If track not found
        409: If track has teams assigned
    """
    # Verify user is organizer
    await check_organizer(zerodb, current_user["id"], hackathon_id)

    logger.info(f"User {current_user['id']} deleting track {track_id}")

    await track_service.delete_track(hackathon_id, track_id, zerodb)

    return None
