"""
Track Service

Business logic for managing hackathon tracks (categories/themes).
Handles CRUD operations with validation and authorization checks.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBTimeoutError,
)

logger = logging.getLogger(__name__)


class TrackService:
    """Service for managing hackathon tracks."""

    def __init__(self, zerodb_client: ZeroDBClient):
        """
        Initialize track service.

        Args:
            zerodb_client: ZeroDB client instance
        """
        self.zerodb = zerodb_client

    async def create_track(
        self,
        hackathon_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> Dict:
        """
        Create a new track for a hackathon.

        Args:
            hackathon_id: UUID of the hackathon
            name: Track name
            description: Optional track description

        Returns:
            Created track record

        Raises:
            HTTPException: 404 if hackathon not found
            HTTPException: 409 if track name already exists for this hackathon
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Verify hackathon exists
            hackathons = await self.zerodb.tables.query_rows(
                "hackathons",
                filter={"hackathon_id": hackathon_id, "is_deleted": False},
            )

            if not hackathons:
                logger.warning(f"Hackathon {hackathon_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Hackathon {hackathon_id} not found",
                )

            # Check for duplicate track name in this hackathon
            existing_tracks = await self.zerodb.tables.query_rows(
                "tracks",
                filter={"hackathon_id": hackathon_id, "name": name},
            )

            if existing_tracks:
                logger.warning(
                    f"Track with name '{name}' already exists for hackathon {hackathon_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Track with name '{name}' already exists for this hackathon",
                )

            # Create track record
            track_id = str(uuid4())
            now = datetime.utcnow()

            track_data = {
                "track_id": track_id,
                "hackathon_id": hackathon_id,
                "name": name,
                "description": description,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            await self.zerodb.tables.insert_rows("tracks", [track_data])

            logger.info(f"Created track {track_id} for hackathon {hackathon_id}")
            return {
                "track_id": track_id,
                "hackathon_id": hackathon_id,
                "name": name,
                "description": description,
                "created_at": now,
                "updated_at": now,
            }

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout creating track: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.error(f"Database error creating track: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create track. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error creating track: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )

    async def list_tracks(self, hackathon_id: str) -> List[Dict]:
        """
        List all tracks for a hackathon.

        Args:
            hackathon_id: UUID of the hackathon

        Returns:
            List of track records

        Raises:
            HTTPException: 404 if hackathon not found
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Verify hackathon exists
            hackathons = await self.zerodb.tables.query_rows(
                "hackathons",
                filter={"hackathon_id": hackathon_id, "is_deleted": False},
            )

            if not hackathons:
                logger.warning(f"Hackathon {hackathon_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Hackathon {hackathon_id} not found",
                )

            # Query tracks
            tracks = await self.zerodb.tables.query_rows(
                "tracks",
                filter={"hackathon_id": hackathon_id},
            )

            # Parse datetime strings
            for track in tracks:
                if "created_at" in track and isinstance(track["created_at"], str):
                    track["created_at"] = datetime.fromisoformat(track["created_at"])
                if "updated_at" in track and isinstance(track["updated_at"], str):
                    track["updated_at"] = datetime.fromisoformat(track["updated_at"])

            logger.info(f"Retrieved {len(tracks)} tracks for hackathon {hackathon_id}")
            return tracks

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout listing tracks: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.error(f"Database error listing tracks: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve tracks. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error listing tracks: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )

    async def get_track(self, hackathon_id: str, track_id: str) -> Dict:
        """
        Get a specific track by ID.

        Args:
            hackathon_id: UUID of the hackathon
            track_id: UUID of the track

        Returns:
            Track record

        Raises:
            HTTPException: 404 if track not found or doesn't belong to hackathon
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Query track
            tracks = await self.zerodb.tables.query_rows(
                "tracks",
                filter={"track_id": track_id, "hackathon_id": hackathon_id},
            )

            if not tracks:
                logger.warning(
                    f"Track {track_id} not found for hackathon {hackathon_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Track {track_id} not found",
                )

            track = tracks[0]

            # Parse datetime strings
            if "created_at" in track and isinstance(track["created_at"], str):
                track["created_at"] = datetime.fromisoformat(track["created_at"])
            if "updated_at" in track and isinstance(track["updated_at"], str):
                track["updated_at"] = datetime.fromisoformat(track["updated_at"])

            logger.info(f"Retrieved track {track_id}")
            return track

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout getting track: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.error(f"Database error getting track: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve track. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error getting track: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )

    async def update_track(
        self,
        hackathon_id: str,
        track_id: str,
        update_data: Dict,
    ) -> Dict:
        """
        Update a track.

        Args:
            hackathon_id: UUID of the hackathon
            track_id: UUID of the track
            update_data: Fields to update

        Returns:
            Updated track record

        Raises:
            HTTPException: 404 if track not found
            HTTPException: 409 if name conflicts with existing track
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Verify track exists and belongs to hackathon
            tracks = await self.zerodb.tables.query_rows(
                "tracks",
                filter={"track_id": track_id, "hackathon_id": hackathon_id},
            )

            if not tracks:
                logger.warning(
                    f"Track {track_id} not found for hackathon {hackathon_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Track {track_id} not found",
                )

            # If name is being updated, check for duplicates
            if "name" in update_data:
                existing_tracks = await self.zerodb.tables.query_rows(
                    "tracks",
                    filter={
                        "hackathon_id": hackathon_id,
                        "name": update_data["name"],
                    },
                )

                # Check if duplicate name belongs to a different track
                if existing_tracks and existing_tracks[0].get("track_id") != track_id:
                    logger.warning(
                        f"Track name '{update_data['name']}' already exists for hackathon {hackathon_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Track with name '{update_data['name']}' already exists for this hackathon",
                    )

            # Update track
            update_data["updated_at"] = datetime.utcnow().isoformat()

            await self.zerodb.tables.update_rows(
                "tracks",
                filter={"track_id": track_id},
                data=update_data,
            )

            # Retrieve updated track
            updated_tracks = await self.zerodb.tables.query_rows(
                "tracks",
                filter={"track_id": track_id},
            )

            track = updated_tracks[0]

            # Parse datetime strings
            if "created_at" in track and isinstance(track["created_at"], str):
                track["created_at"] = datetime.fromisoformat(track["created_at"])
            if "updated_at" in track and isinstance(track["updated_at"], str):
                track["updated_at"] = datetime.fromisoformat(track["updated_at"])

            logger.info(f"Updated track {track_id}")
            return track

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout updating track: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.error(f"Database error updating track: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update track. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error updating track: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )

    async def delete_track(self, hackathon_id: str, track_id: str) -> Dict:
        """
        Delete a track.

        Args:
            hackathon_id: UUID of the hackathon
            track_id: UUID of the track

        Returns:
            Deletion confirmation

        Raises:
            HTTPException: 404 if track not found
            HTTPException: 500 for database errors
            HTTPException: 504 for timeout errors
        """
        try:
            # Verify track exists and belongs to hackathon
            tracks = await self.zerodb.tables.query_rows(
                "tracks",
                filter={"track_id": track_id, "hackathon_id": hackathon_id},
            )

            if not tracks:
                logger.warning(
                    f"Track {track_id} not found for hackathon {hackathon_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Track {track_id} not found",
                )

            # Delete track
            await self.zerodb.tables.delete_rows(
                "tracks",
                filter={"track_id": track_id},
            )

            logger.info(f"Deleted track {track_id}")
            return {
                "success": True,
                "track_id": track_id,
                "message": "Track successfully deleted",
            }

        except HTTPException:
            raise

        except ZeroDBTimeoutError as e:
            logger.error(f"Timeout deleting track: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again.",
            )

        except (ZeroDBError, ZeroDBNotFound) as e:
            logger.error(f"Database error deleting track: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete track. Please contact support.",
            )

        except Exception as e:
            logger.error(f"Unexpected error deleting track: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please contact support.",
            )


# Module-level wrapper functions for use by route handlers.
# Each function instantiates TrackService with the provided zerodb client
# and delegates to the corresponding instance method.


async def create_track(
    hackathon_id: str,
    name: str,
    description: Optional[str] = None,
    zerodb: ZeroDBClient = None,
) -> Dict:
    """Create a new track for a hackathon."""
    service = TrackService(zerodb)
    return await service.create_track(hackathon_id, name, description)


async def list_tracks(hackathon_id: str, zerodb: ZeroDBClient = None) -> Dict:
    """List all tracks for a hackathon."""
    service = TrackService(zerodb)
    tracks = await service.list_tracks(hackathon_id)
    return {"tracks": tracks, "total": len(tracks)}


async def get_track(
    hackathon_id: str, track_id: str, zerodb: ZeroDBClient = None
) -> Dict:
    """Get a specific track by ID."""
    service = TrackService(zerodb)
    return await service.get_track(hackathon_id, track_id)


async def update_track(
    hackathon_id: str,
    track_id: str,
    update_data: Dict,
    zerodb: ZeroDBClient = None,
) -> Dict:
    """Update a track."""
    service = TrackService(zerodb)
    return await service.update_track(hackathon_id, track_id, update_data)


async def delete_track(
    hackathon_id: str, track_id: str, zerodb: ZeroDBClient = None
) -> Dict:
    """Delete a track."""
    service = TrackService(zerodb)
    return await service.delete_track(hackathon_id, track_id)
